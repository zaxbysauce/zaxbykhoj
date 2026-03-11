"""Authentication and user configuration helpers."""

import json
import logging
import os
from typing import Optional

from starlette.authentication import has_required_scope
from starlette.requests import Request
from starlette.responses import Response

from khoj.database import adapters
from khoj.database.adapters import (
    LENGTH_OF_FREE_TRIAL,
    ConversationAdapters,
    EntryAdapters,
    get_user_name,
    get_user_notion_config,
    get_user_subscription_state,
)
from khoj.database.models import (
    GithubConfig,
    KhojUser,
    NotionConfig,
    ServerChatSettings,
)
from khoj.processor.content.docx.docx_to_entries import DocxToEntries
from khoj.processor.content.github.github_to_entries import GithubToEntries
from khoj.processor.content.images.image_to_entries import ImageToEntries
from khoj.processor.content.markdown.markdown_to_entries import MarkdownToEntries
from khoj.processor.content.notion.notion_to_entries import NotionToEntries
from khoj.processor.content.org_mode.org_to_entries import OrgToEntries
from khoj.processor.content.pdf.pdf_to_entries import PdfToEntries
from khoj.processor.content.plaintext.plaintext_to_entries import PlaintextToEntries
from khoj.processor.speech.text_to_speech import is_eleven_labs_enabled
from khoj.routers.twilio import is_twilio_enabled
from khoj.search_type import text_search
from khoj.utils import state
from khoj.utils.config import ApiUrlConfig

logger = logging.getLogger(__name__)


NOTION_OAUTH_CLIENT_ID = os.getenv("NOTION_OAUTH_CLIENT_ID")
NOTION_OAUTH_CLIENT_SECRET = os.getenv("NOTION_OAUTH_CLIENT_SECRET")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI")


def get_user_config(user: KhojUser, request: Request, is_detailed: bool = False):
    user_picture = request.session.get("user", {}).get("picture")
    is_active = has_required_scope(request, ["premium"])
    has_documents = EntryAdapters.user_has_entries(user=user)

    if not is_detailed:
        return {
            "request": request,
            "username": user.username if user else None,
            "user_photo": user_picture,
            "is_active": is_active,
            "has_documents": has_documents,
            "khoj_version": state.khoj_version,
            "is_admin": user.is_staff or user.is_superuser if user else False,
        }

    user_subscription_state = get_user_subscription_state(user.email)
    user_subscription = adapters.get_user_subscription(user.email)

    subscription_renewal_date = (
        user_subscription.renewal_date.strftime("%d %b %Y")
        if user_subscription and user_subscription.renewal_date
        else None
    )
    subscription_enabled_trial_at = (
        user_subscription.enabled_trial_at.strftime("%d %b %Y")
        if user_subscription and user_subscription.enabled_trial_at
        else None
    )
    given_name = get_user_name(user)

    enabled_content_sources_set = set(EntryAdapters.get_unique_file_sources(user))
    enabled_content_sources = {
        "computer": ("computer" in enabled_content_sources_set),
        "github": ("github" in enabled_content_sources_set),
        "notion": ("notion" in enabled_content_sources_set),
    }

    notion_oauth_url = get_notion_auth_url(user)
    current_notion_config = get_user_notion_config(user)
    notion_token = current_notion_config.token if current_notion_config else ""

    selected_chat_model_config = ConversationAdapters.get_chat_model(
        user
    ) or ConversationAdapters.get_default_chat_model(user)
    server_chat_settings = ServerChatSettings.objects.first()
    server_memory_mode = (
        server_chat_settings.memory_mode
        if server_chat_settings
        else ServerChatSettings.MemoryMode.ENABLED_DEFAULT_ON.value  # type: ignore[attr-defined]
    )
    enable_memory = ConversationAdapters.is_memory_enabled(user)
    chat_models = ConversationAdapters.get_conversation_processor_options().all()
    chat_model_options = list()
    for chat_model in chat_models:
        chat_model_options.append(
            {
                "name": chat_model.friendly_name,
                "id": chat_model.id,
                "strengths": chat_model.strengths,
                "description": chat_model.description,
                "tier": chat_model.price_tier,
            }
        )

    selected_paint_model_config = ConversationAdapters.get_user_text_to_image_model_config(user)
    paint_model_options = ConversationAdapters.get_text_to_image_model_options().all()
    all_paint_model_options = list()
    for paint_model in paint_model_options:
        all_paint_model_options.append(
            {
                "name": paint_model.friendly_name,
                "id": paint_model.id,
                "tier": paint_model.price_tier,
            }
        )

    voice_models = ConversationAdapters.get_voice_model_options()
    voice_model_options = list()
    for voice_model in voice_models:
        voice_model_options.append(
            {
                "name": voice_model.name,
                "id": voice_model.model_id,
                "tier": voice_model.price_tier,
            }
        )

    if len(voice_model_options) == 0:
        eleven_labs_enabled = False
    else:
        eleven_labs_enabled = is_eleven_labs_enabled()

    selected_voice_model_config = ConversationAdapters.get_voice_model_config(user)

    return {
        "request": request,
        # user info
        "username": user.username if user else None,
        "user_photo": user_picture,
        "is_active": is_active,
        "is_admin": user.is_staff or user.is_superuser if user else False,
        "given_name": given_name,
        "phone_number": str(user.phone_number) if user.phone_number else "",
        "is_phone_number_verified": user.verified_phone_number,
        # user content settings
        "enabled_content_source": enabled_content_sources,
        "has_documents": has_documents,
        "notion_token": notion_token,
        "enable_memory": enable_memory,
        "server_memory_mode": server_memory_mode,
        # user model settings
        "chat_model_options": chat_model_options,
        "selected_chat_model_config": selected_chat_model_config.id if selected_chat_model_config else None,
        "paint_model_options": all_paint_model_options,
        "selected_paint_model_config": selected_paint_model_config.id if selected_paint_model_config else None,
        "voice_model_options": voice_model_options,
        "selected_voice_model_config": selected_voice_model_config.model_id if selected_voice_model_config else None,
        # user billing info
        "subscription_state": user_subscription_state,
        "subscription_renewal_date": subscription_renewal_date,
        "subscription_enabled_trial_at": subscription_enabled_trial_at,
        # server settings
        "khoj_cloud_subscription_url": os.getenv("KHOJ_CLOUD_SUBSCRIPTION_URL"),
        "billing_enabled": state.billing_enabled,
        "is_eleven_labs_enabled": eleven_labs_enabled,
        "is_twilio_enabled": is_twilio_enabled(),
        "khoj_version": state.khoj_version,
        "anonymous_mode": state.anonymous_mode,
        "notion_oauth_url": notion_oauth_url,
        "length_of_free_trial": LENGTH_OF_FREE_TRIAL,
    }


def user_config_to_response(
    user: KhojUser,
    request: Request,
    is_detailed: bool = False,
    extra_config: Optional[dict] = None,
) -> Response:
    """Get user config and return as JSON Response.

    Args:
        user: The authenticated user
        request: The incoming request (used to get session data)
        is_detailed: Whether to include detailed subscription info
        extra_config: Optional additional config to merge into user_config

    Returns:
        Response with user config as JSON
    """
    user_config = get_user_config(user, request, is_detailed=is_detailed)
    del user_config["request"]

    if extra_config:
        user_config.update(extra_config)

    return Response(content=json.dumps(user_config), media_type="application/json", status_code=200)


def configure_content(
    user: KhojUser,
    files: Optional[dict[str, dict[str, str]]],
    regenerate: bool = False,
    t: Optional[state.SearchType] = state.SearchType.All,
) -> bool:
    success = True
    if t is None:
        t = state.SearchType.All

    if t is not None and t in [type.value for type in state.SearchType]:
        t = state.SearchType(t)

    if t is not None and t.value not in [type.value for type in state.SearchType]:
        logger.warning(f"🚨 Invalid search type: {t}")
        return False

    search_type = t.value if t else None

    # Check if client sent any documents of the supported types
    no_client_sent_documents = all([not files.get(file_type) for file_type in files])

    if files is None:
        logger.warning(f"🚨 No files to process for {search_type} search.")
        return True

    try:
        # Initialize Org Notes Search
        if (search_type == state.SearchType.All.value or search_type == state.SearchType.Org.value) and files.get(
            "org"
        ):
            logger.info("🦄 Setting up search for orgmode notes")
            # Extract Entries, Generate Notes Embeddings
            text_search.setup(
                OrgToEntries,
                files.get("org"),
                regenerate=regenerate,
                user=user,
            )
    except Exception as e:
        logger.error(f"🚨 Failed to setup org: {e}", exc_info=True)
        success = False

    try:
        # Initialize Markdown Search
        if (search_type == state.SearchType.All.value or search_type == state.SearchType.Markdown.value) and files.get(
            "markdown"
        ):
            logger.info("💎 Setting up search for markdown notes")
            # Extract Entries, Generate Markdown Embeddings
            text_search.setup(
                MarkdownToEntries,
                files.get("markdown"),
                regenerate=regenerate,
                user=user,
            )

    except Exception as e:
        logger.error(f"🚨 Failed to setup markdown: {e}", exc_info=True)
        success = False

    try:
        # Initialize PDF Search
        if (search_type == state.SearchType.All.value or search_type == state.SearchType.Pdf.value) and files.get(
            "pdf"
        ):
            logger.info("🖨️ Setting up search for pdf")
            # Extract Entries, Generate PDF Embeddings
            text_search.setup(
                PdfToEntries,
                files.get("pdf"),
                regenerate=regenerate,
                user=user,
            )

    except Exception as e:
        logger.error(f"🚨 Failed to setup PDF: {e}", exc_info=True)
        success = False

    try:
        # Initialize Plaintext Search
        if (search_type == state.SearchType.All.value or search_type == state.SearchType.Plaintext.value) and files.get(
            "plaintext"
        ):
            logger.info("📄 Setting up search for plaintext")
            # Extract Entries, Generate Plaintext Embeddings
            text_search.setup(
                PlaintextToEntries,
                files.get("plaintext"),
                regenerate=regenerate,
                user=user,
            )

    except Exception as e:
        logger.error(f"🚨 Failed to setup plaintext: {e}", exc_info=True)
        success = False

    try:
        # Run server side indexing of user Github docs if no client sent documents
        if no_client_sent_documents:
            github_config = GithubConfig.objects.filter(user=user).prefetch_related("githubrepoconfig").first()
            if (
                search_type == state.SearchType.All.value or search_type == state.SearchType.Github.value
            ) and github_config is not None:
                logger.info("🐙 Setting up search for github")
                # Extract Entries, Generate Github Embeddings
                text_search.setup(
                    GithubToEntries,
                    None,
                    regenerate=regenerate,
                    user=user,
                    config=github_config,
                )

    except Exception as e:
        logger.error(f"🚨 Failed to setup GitHub: {e}", exc_info=True)
        success = False

    try:
        # Run server side indexing of user Notion docs if no client sent documents
        if no_client_sent_documents:
            # Initialize Notion Search
            notion_config = NotionConfig.objects.filter(user=user).first()
            if (
                search_type == state.SearchType.All.value or search_type == state.SearchType.Notion.value
            ) and notion_config:
                logger.info("🔌 Setting up search for notion")
                text_search.setup(
                    NotionToEntries,
                    None,
                    regenerate=regenerate,
                    user=user,
                    config=notion_config,
                )

    except Exception as e:
        logger.error(f"🚨 Failed to setup Notion: {e}", exc_info=True)
        success = False

    try:
        # Initialize Image Search
        if (search_type == state.SearchType.All.value or search_type == state.SearchType.Image.value) and files[
            "image"
        ]:
            logger.info("🖼️ Setting up search for images")
            # Extract Entries, Generate Image Embeddings
            text_search.setup(
                ImageToEntries,
                files.get("image"),
                regenerate=regenerate,
                user=user,
            )
    except Exception as e:
        logger.error(f"🚨 Failed to setup images: {e}", exc_info=True)
        success = False
    try:
        if (search_type == state.SearchType.All.value or search_type == state.SearchType.Docx.value) and files["docx"]:
            logger.info("📄 Setting up search for docx")
            text_search.setup(
                DocxToEntries,
                files.get("docx"),
                regenerate=regenerate,
                user=user,
            )
    except Exception as e:
        logger.error(f"🚨 Failed to setup docx: {e}", exc_info=True)
        success = False

    # Invalidate Query Cache
    if user:
        state.query_cache[user.uuid] = LRU()

    return success


def get_notion_auth_url(user: KhojUser):
    if not NOTION_OAUTH_CLIENT_ID or not NOTION_OAUTH_CLIENT_SECRET or not NOTION_REDIRECT_URI:
        return None
    return f"{ApiUrlConfig.NOTION_API_URL}/oauth/authorize?client_id={NOTION_OAUTH_CLIENT_ID}&redirect_uri={NOTION_REDIRECT_URI}&response_type=code&state={user.uuid}"
