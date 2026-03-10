"""
Vector and embedding-related helper functions for the Khoj API.

This module contains functions for:
- Query embedding and vector search
- Search result processing
- Query extraction for semantic search
"""

import asyncio
import logging
import time
from typing import (
    Callable,
    List,
    Optional,
    Set,
    Union,
)

from asgiref.sync import sync_to_async

from khoj.database.adapters import (
    AgentAdapters,
    EntryAdapters,
)
from khoj.database.models import (
    Agent,
    ChatMessageModel,
    ConversationCommand,
    KhojUser,
    LocationData,
    UserMemory,
)
from khoj.processor.conversation import prompts
from khoj.processor.conversation.utils import clean_json, construct_question_history
from khoj.search_filter.date_filter import DateFilter
from khoj.search_filter.file_filter import FileFilter
from khoj.search_filter.word_filter import WordFilter
from khoj.search_type import text_search
from khoj.utils import state
from khoj.utils.helpers import (
    defilter_query,
    get_default_search_model,
    is_none_or_empty,
    timer,
)
from khoj.utils.rawconfig import SearchResponse
from khoj.utils.state import ChatEvent, SearchType

logger = logging.getLogger(__name__)


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
    """
    Execute a vector search against the user's indexed data.

    This function:
    1. Embeds the query using the configured search model
    2. Performs similarity search against indexed entries
    3. Returns ranked search results
    """
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
    """
    Search indexed documents and return compiled references for chat context.

    This function:
    1. Extracts search queries from the user message using LLM
    2. Executes vector searches for each query
    3. Compiles and returns search results as references
    """
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

    # Lazy import to avoid circular dependency
    from khoj.database.adapters import ConversationAdapters

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
    Infer document search queries from user message and provided context.

    This uses an LLM to generate multiple semantic search queries from
    the user's natural language query to improve recall.
    """
    from datetime import datetime, timedelta

    import pyjson5
    from pydantic import BaseModel, Field

    from khoj.database.adapters import AgentAdapters

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
