import asyncio
import fnmatch
import logging
import re
import time
from datetime import datetime, timedelta
from typing import (
    Callable,
    List,
    Optional,
    Set,
    Union,
)

import pyjson5
from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field

from khoj.database.adapters import (
    AgentAdapters,
    ConversationAdapters,
    EntryAdapters,
    FileObjectAdapters,
    get_default_search_model,
)
from khoj.database.models import (
    Agent,
    ChatMessageModel,
    KhojUser,
    UserMemory,
)
from khoj.processor.conversation import prompts
from khoj.processor.conversation.utils import ChatEvent, clean_json, construct_question_history, defilter_query
from khoj.search_filter.date_filter import DateFilter
from khoj.search_filter.file_filter import FileFilter
from khoj.search_filter.word_filter import WordFilter
from khoj.search_type import text_search
from khoj.utils import state
from khoj.utils.helpers import (
    ConversationCommand,
    is_none_or_empty,
    timer,
)
from khoj.utils.rawconfig import LocationData, SearchResponse
from khoj.utils.state import SearchType

logger = logging.getLogger(__name__)


async def search_documents(
    q: str,
    n: int,
    d: float,
    user: KhojUser,
    chat_history: list[ChatMessageModel],
    conversation_id: str,
    conversation_commands: List[ConversationCommand] = [ConversationCommand.Notes],
    location_data: LocationData = None,
    send_status_func: Optional[Callable] = None,
    query_images: Optional[List[str]] = None,
    query_files: str = None,
    relevant_memories: List[UserMemory] = None,
    previous_inferred_queries: Set = set(),
    fast_model: bool = True,
    agent: Agent = None,
    tracer: dict = {},
):
    # Initialize Variables
    compiled_references: List[dict[str, str]] = []
    inferred_queries: List[str] = []

    agent_has_entries = False

    if agent:
        agent_has_entries = await sync_to_async(EntryAdapters.agent_has_entries)(agent=agent)

    if ConversationCommand.Notes not in conversation_commands and not agent_has_entries:
        yield compiled_references, inferred_queries, q
        return

    # If Notes is not in the conversation command, then the search should be restricted to the agent's knowledge base
    should_limit_to_agent_knowledge = ConversationCommand.Notes not in conversation_commands

    if not await sync_to_async(EntryAdapters.user_has_entries)(user=user):
        if not agent_has_entries:
            logger.debug("No documents in knowledge base. Use a Khoj client to sync and chat with your docs.")
            yield compiled_references, inferred_queries, q
            return

    # Extract filter terms from user message
    defiltered_query = defilter_query(q)
    filters_in_query = q.replace(defiltered_query, "").strip()
    conversation = await sync_to_async(ConversationAdapters.get_conversation_by_id)(conversation_id)

    if not conversation:
        logger.error(f"Conversation with id {conversation_id} not found when extracting references.", exc_info=True)
        yield compiled_references, inferred_queries, defiltered_query
        return

    filters_in_query += " ".join([f'file:"{filter}"' for filter in conversation.file_filters])
    if is_none_or_empty(filters_in_query):
        logger.debug(f"Filters in query: {filters_in_query}")

    personality_context = prompts.personality_context.format(personality=agent.personality) if agent else ""

    # Infer search queries from user message
    with timer("Extracting search queries took", logger):
        inferred_queries = await extract_questions(
            query=defiltered_query,
            user=user,
            query_files=query_files,
            query_images=query_images,
            relevant_memories=relevant_memories,
            personality_context=personality_context,
            location_data=location_data,
            chat_history=chat_history,
            fast_model=fast_model,
            agent=agent,
            tracer=tracer,
        )

    # Collate search results as context for the LLM
    inferred_queries = list(set(inferred_queries) - previous_inferred_queries)
    with timer("Searching knowledge base took", logger):
        search_results = []
        logger.info(f"🔍 Searching knowledge base with queries: {inferred_queries}")
        if send_status_func:
            inferred_queries_str = "\n- " + "\n- ".join(inferred_queries)
            async for event in send_status_func(f"**Searching Documents for:** {inferred_queries_str}"):
                yield {ChatEvent.STATUS: event}
        for query in inferred_queries:
            results = await execute_search(
                user if not should_limit_to_agent_knowledge else None,
                f"{query} {filters_in_query}",
                n=n,
                t=SearchType.All,
                r=True,
                max_distance=d,
                dedupe=False,
                agent=agent,
            )
            # Attach associated query to each search result
            for item in results:
                item.additional["query"] = query
                search_results.append(item)

        search_results = text_search.deduplicated_search_responses(search_results)
        compiled_references = [
            {
                "query": item.additional["query"],
                "compiled": item["entry"],
                "file": item.additional["file"],
                "uri": item.additional["uri"],
            }
            for item in search_results
        ]

    yield compiled_references, inferred_queries, defiltered_query


async def extract_questions(
    query: str,
    user: KhojUser,
    query_files: str = None,
    query_images: Optional[List[str]] = None,
    personality_context: str = "",
    relevant_memories: List[UserMemory] = None,
    location_data: LocationData = None,
    chat_history: List[ChatMessageModel] = [],
    max_queries: int = 5,
    fast_model: bool = True,
    agent: Agent = None,
    tracer: dict = {},
):
    """
    Infer document search queries from user message and provided context
    """
    # Shared context setup
    location = f"{location_data}" if location_data else "N/A"
    username = prompts.user_name.format(name=user.get_full_name()) if user and user.get_full_name() else ""

    # Date variables for prompt formatting
    today = datetime.today()
    current_new_year = today.replace(month=1, day=1)
    last_new_year = current_new_year.replace(year=today.year - 1)
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # Common prompt setup for API-based models (using Anthropic prompts for consistency)
    chat_history_str = construct_question_history(chat_history, query_prefix="User", agent_name="Assistant")

    system_prompt = prompts.extract_questions_system_prompt.format(
        current_date=today.strftime("%Y-%m-%d"),
        day_of_week=today.strftime("%A"),
        current_month=today.strftime("%Y-%m"),
        last_new_year=last_new_year.strftime("%Y"),
        last_new_year_date=last_new_year.strftime("%Y-%m-%d"),
        current_new_year_date=current_new_year.strftime("%Y-%m-%d"),
        yesterday_date=yesterday,
        location=location,
        username=username,
        personality_context=personality_context,
        max_queries=max_queries,
    )

    prompt = prompts.extract_questions_user_message.format(text=query, chat_history=chat_history_str)

    class DocumentQueries(BaseModel):
        """Choose semantic search queries to run on user documents."""

        queries: List[str] = Field(
            ...,
            min_length=1,
            max_length=max_queries,
            description="List of semantic search queries to run on user documents.",
        )

    agent_chat_model = AgentAdapters.get_agent_chat_model(agent, user) if agent else None

    # Lazy import to avoid circular dependency
    from khoj.routers.helpers import send_message_to_model_wrapper

    raw_response = await send_message_to_model_wrapper(
        query=prompt,
        query_files=query_files,
        query_images=query_images,
        relevant_memories=relevant_memories,
        system_message=system_prompt,
        response_type="json_object",
        response_schema=DocumentQueries,
        fast_model=fast_model,
        agent_chat_model=agent_chat_model,
        user=user,
        tracer=tracer,
    )

    # Extract questions from the response
    try:
        response = clean_json(raw_response.text)
        response = pyjson5.loads(response)
        queries = [q.strip() for q in response["queries"] if q.strip()]
        if not isinstance(queries, list) or not queries:
            logger.error(f"Invalid response for constructing subqueries: {response}", exc_info=True)
            return [query]
        return queries
    except Exception:
        logger.warning("LLM returned invalid JSON. Falling back to using user message as search query.", exc_info=True)
        return [query]


async def execute_search(
    user: KhojUser,
    q: str,
    n: Optional[int] = 5,
    t: Optional[SearchType] = None,
    r: Optional[bool] = False,
    max_distance: Optional[Union[float, None]] = None,
    dedupe: Optional[bool] = True,
    agent: Optional[Agent] = None,
):
    # Run validation checks
    results: List[SearchResponse] = []

    start_time = time.time()

    # Ensure the agent, if present, is accessible by the user
    if user and agent and not await AgentAdapters.ais_agent_accessible(agent, user):
        logger.error(f"Agent {agent.slug} is not accessible by user {user}", exc_info=True)
        return results

    if q is None or q == "":
        logger.warning("No query param (q) passed in API call to initiate search")
        return results

    # initialize variables
    user_query = q.strip()
    results_count = n or 5
    t = t or state.SearchType.All
    search_tasks = []

    # return cached results, if available
    if user:
        query_cache_key = f"{user_query}-{n}-{t}-{r}-{max_distance}-{dedupe}"
        if query_cache_key in state.query_cache[user.uuid]:
            logger.debug("Return response from query cache")
            return state.query_cache[user.uuid][query_cache_key]

    # Encode query with filter terms removed
    defiltered_query = user_query
    for filter in [DateFilter(), WordFilter(), FileFilter()]:
        defiltered_query = filter.defilter(defiltered_query)

    encoded_asymmetric_query = None
    if t.value != SearchType.Image.value:
        with timer("Encoding query took", logger=logger):
            search_model = await sync_to_async(get_default_search_model)()
            encoded_asymmetric_query = state.embeddings_model[search_model.name].embed_query(defiltered_query)

    # Use asyncio to run searches in parallel
    if t.value in [
        SearchType.All.value,
        SearchType.Org.value,
        SearchType.Markdown.value,
        SearchType.Github.value,
        SearchType.Notion.value,
        SearchType.Plaintext.value,
        SearchType.Pdf.value,
    ]:
        # query markdown notes
        search_tasks.append(
            text_search.query(
                user_query,
                user,
                t,
                question_embedding=encoded_asymmetric_query,
                max_distance=max_distance,
                agent=agent,
            )
        )

    # Query across each requested content types in parallel
    with timer("Query took", logger):
        if search_tasks:
            hits_list = await asyncio.gather(*search_tasks)
            for hits in hits_list:
                # Collate results
                results += text_search.collate_results(hits, dedupe=dedupe)

                # Sort results across all content types and take top results
                results = text_search.rerank_and_sort_results(
                    results, query=defiltered_query, rank_results=r, search_model_name=search_model.name
                )[:results_count]

    # Cache results
    if user:
        state.query_cache[user.uuid][query_cache_key] = results

    end_time = time.time()
    logger.debug(f"🔍 Search took: {end_time - start_time:.3f} seconds")

    return results


async def grep_files(
    regex_pattern: str,
    path_prefix: Optional[str] = None,
    lines_before: Optional[int] = None,
    lines_after: Optional[int] = None,
    user: KhojUser = None,
):
    """
    Search for a regex pattern in files with an optional path prefix and context lines.
    """

    # Construct the query string based on provided parameters
    def _generate_query(line_count, doc_count, path, pattern, lines_before, lines_after, max_results=1000):
        query = f"**Found {line_count} matches for '{pattern}' in {doc_count} documents**"
        if path:
            query += f" in {path}"
        if lines_before or lines_after or line_count > max_results:
            query += " Showing"
        if lines_before or lines_after:
            context_info = []
            if lines_before:
                context_info.append(f"{lines_before} lines before")
            if lines_after:
                context_info.append(f"{lines_after} lines after")
            query += f" {' and '.join(context_info)}"
        if line_count > max_results:
            if lines_before or lines_after:
                query += " for"
            query += f" first {max_results} results"
        return query

    # Validate regex pattern
    path_prefix = path_prefix or ""
    lines_before = lines_before or 0
    lines_after = lines_after or 0

    try:
        regex = re.compile(regex_pattern, re.IGNORECASE | re.MULTILINE)
    except re.error as e:
        yield {
            "query": _generate_query(0, 0, path_prefix, regex_pattern, lines_before, lines_after),
            "file": path_prefix,
            "compiled": f"Invalid regex pattern: {e}",
        }
        return

    try:
        # Make db pushdown filters more permissive by removing line anchors
        # The precise line-anchored matching will be done in Python stage
        db_pattern = regex_pattern
        db_pattern = re.sub(r"\(\?\w*\)", "", db_pattern)  # Remove inline flags like (?i), (?m), (?im)
        db_pattern = re.sub(r"^\^", "", db_pattern)  # Remove ^ at regex pattern start
        db_pattern = re.sub(r"\$$", "", db_pattern)  # Remove $ at regex pattern end

        file_matches = await FileObjectAdapters.aget_file_objects_by_regex(user, db_pattern, path_prefix)

        line_matches = []
        line_matches_count = 0
        for file_object in file_matches:
            lines = file_object.raw_text.split("\n")
            matched_line_numbers = []

            # Find all matching line numbers first
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    matched_line_numbers.append(i)
            line_matches_count += len(matched_line_numbers)

            # Build context for each match
            for line_num in matched_line_numbers:
                context_lines = []

                # Calculate start and end indices for context (0-based)
                start_idx = max(0, line_num - 1 - lines_before)
                end_idx = min(len(lines), line_num + lines_after)

                # Add context lines with line numbers
                for idx in range(start_idx, end_idx):
                    current_line_num = idx + 1
                    line_content = lines[idx]

                    if current_line_num == line_num:
                        # This is the matching line, mark it
                        context_lines.append(f"{file_object.file_name}:{current_line_num}: {line_content}")
                    else:
                        # This is a context line
                        context_lines.append(f"{file_object.file_name}-{current_line_num}-  {line_content}")

                # Add separator between matches if showing context
                if lines_before > 0 or lines_after > 0:
                    context_lines.append("--")

                line_matches.extend(context_lines)

        # Remove the last separator if it exists
        if line_matches and line_matches[-1] == "--":
            line_matches.pop()

        # Check if no results found
        max_results = 1000
        query = _generate_query(
            line_matches_count,
            len(file_matches),
            path_prefix,
            regex_pattern,
            lines_before,
            lines_after,
            max_results,
        )
        if not line_matches:
            yield {"query": query, "file": path_prefix, "uri": path_prefix, "compiled": "No matches found."}
            return

        # Truncate matched lines list if too long
        if len(line_matches) > max_results:
            line_matches = line_matches[:max_results] + [
                f"... {len(line_matches) - max_results} more results found. Use stricter regex or path to narrow down results."
            ]

        yield {"query": query, "file": path_prefix, "uri": path_prefix, "compiled": "\n".join(line_matches)}

    except Exception as e:
        error_msg = f"Error using grep files tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield [
            {
                "query": _generate_query(0, 0, path_prefix or "", regex_pattern, lines_before, lines_after),
                "file": path_prefix,
                "uri": path_prefix,
                "compiled": error_msg,
            }
        ]


async def list_files(
    path: Optional[str] = None,
    pattern: Optional[str] = None,
    user: KhojUser = None,
):
    """
    List files under a given path or glob pattern from the user's document database.
    """

    # Construct the query string based on provided parameters
    def _generate_query(doc_count, path, pattern):
        query = f"**Found {doc_count} files**"
        if path:
            query += f" in {path}"
        if pattern:
            query += f" filtered by {pattern}"
        return query

    try:
        # Get user files by path prefix when specified
        path = path or ""
        if path in ["", "/", ".", "./", "~", "~/"]:
            file_objects = await FileObjectAdapters.aget_all_file_objects(user, limit=10000)
        else:
            file_objects = await FileObjectAdapters.aget_file_objects_by_path_prefix(user, path)

        if not file_objects:
            yield {"query": _generate_query(0, path, pattern), "file": path, "uri": path, "compiled": "No files found."}
            return

        # Extract file names from file objects
        files = [f.file_name for f in file_objects]
        # Convert to relative file path (similar to ls)
        if path:
            files = [f[len(path) :] for f in files]

        # Apply glob pattern filtering if specified
        if pattern:
            files = [f for f in files if fnmatch.fnmatch(f, pattern)]

        query = _generate_query(len(files), path, pattern)
        if not files:
            yield {"query": query, "file": path, "uri": path, "compiled": "No files found."}
            return

        # Truncate the list if it's too long
        max_files = 100
        if len(files) > max_files:
            files = files[:max_files] + [
                f"... {len(files) - max_files} more files found. Use glob pattern to narrow down results."
            ]

        yield {"query": query, "file": path, "uri": path, "compiled": "\n- ".join(files)}

    except Exception as e:
        error_msg = f"Error listing files in {path}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield {"query": _generate_query(0, path, pattern), "file": path, "uri": path, "compiled": error_msg}
