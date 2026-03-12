"""LDAP Configuration and Authentication API Router."""
import logging
from typing import Optional

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, validator

from khoj.database.models import KhojUser, LdapConfig
from khoj.processor.auth import LdapAuthBackend, LdapAuthError
from khoj.utils.secrets import LdapSecretError, has_ldap_credentials
from khoj.utils.secrets_vault import is_vault_configured

logger = logging.getLogger(__name__)

router = APIRouter(tags=["LDAP"])


# Pydantic models for request/response
class LdapConfigResponse(BaseModel):
    """LDAP configuration response (password excluded)."""

    server_url: str
    user_search_base: str
    user_search_filter: str
    use_tls: bool
    tls_verify: bool
    tls_ca_bundle_path: Optional[str] = None
    enabled: bool
    bind_dn: Optional[str] = None
    has_bind_password: bool = False


class LdapConfigRequest(BaseModel):
    """LDAP configuration request."""

    server_url: str = Field(..., description="LDAP server URL (e.g., ldaps://ad.company.com:636)")
    user_search_base: str = Field(..., description="Base DN for user searches")
    user_search_filter: str = Field(default="(sAMAccountName={username})", description="Search filter template")
    use_tls: bool = Field(default=True, description="Use TLS/SSL")
    tls_verify: bool = Field(default=True, description="Verify TLS certificates")
    tls_ca_bundle_path: Optional[str] = Field(default=None, description="Path to custom CA bundle")
    enabled: bool = Field(default=False, description="Enable LDAP authentication")
    bind_dn: Optional[str] = Field(default=None, description="LDAP service account bind DN")
    bind_password: Optional[str] = Field(default=None, description="LDAP service account bind password")

    @validator("server_url")
    def validate_server_url(cls, v):
        if not v.startswith(("ldap://", "ldaps://")):
            raise ValueError("server_url must start with ldap:// or ldaps://")
        return v


class LdapTestRequest(BaseModel):
    """LDAP connection test request."""

    server_url: str
    user_search_base: str
    user_search_filter: str = "(sAMAccountName={username})"
    use_tls: bool = True
    tls_verify: bool = True
    tls_ca_bundle_path: Optional[str] = None
    bind_dn: Optional[str] = None
    bind_password: Optional[str] = None


class LdapTestResponse(BaseModel):
    """LDAP connection test response."""

    success: bool
    message: str


class LdapLoginRequest(BaseModel):
    """LDAP login request."""

    username: str = Field(..., min_length=1, max_length=256, description="LDAP username")
    password: str = Field(..., min_length=1, description="LDAP password")


class LdapLoginResponse(BaseModel):
    """LDAP login response."""

    success: bool
    message: str
    user_id: Optional[str] = None


class LdapManagedUser(BaseModel):
    """LDAP-provisioned user details for admin management."""

    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    ldap_dn: str
    is_active: bool
    is_admin: bool


class LdapUserUpdateRequest(BaseModel):
    """Admin update payload for LDAP users."""

    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


# Rate limiting storage (in production, use Redis)
_auth_attempts = {}


def _check_rate_limit(identifier: str, max_attempts: int = 5, window: int = 60) -> bool:
    """Check if request is within rate limit."""
    import time
    from collections import deque

    now = time.time()

    if identifier not in _auth_attempts:
        _auth_attempts[identifier] = deque()

    attempts = _auth_attempts[identifier]
    while attempts and attempts[0] < now - window:
        attempts.popleft()

    if len(attempts) >= max_attempts:
        return False

    attempts.append(now)
    return True


def get_current_user(request: Request) -> KhojUser:
    """Get the authenticated Django user from the request."""
    if not hasattr(request, "user") or not request.user.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return request.user.object


def require_admin(user: KhojUser = Depends(get_current_user)) -> KhojUser:
    """Require admin access for LDAP settings."""
    if not user.is_staff and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def _maybe_update_bind_credentials(bind_dn: Optional[str], bind_password: Optional[str]) -> bool:
    """Validate that bind credential inputs are consistent (both or neither)."""
    dn_provided = bind_dn is not None and bind_dn.strip() != ""
    pw_provided = bind_password is not None and bind_password.strip() != ""

    if not dn_provided and not pw_provided:
        return False

    if not dn_provided or not pw_provided:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both bind_dn and bind_password are required when updating LDAP credentials.",
        )

    return True


def _config_has_credentials(config: LdapConfig) -> bool:
    """Return True if the config has a bind_dn and an encrypted password."""
    return bool(config.bind_dn and config.has_bind_password())


@router.get("/api/settings/ldap", response_model=LdapConfigResponse)
async def get_ldap_config(admin: KhojUser = Depends(require_admin)):
    """Get current LDAP configuration (admin only)."""
    config = await LdapConfig.objects.filter().afirst()

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LDAP configuration not found")

    return LdapConfigResponse(
        server_url=config.server_url,
        user_search_base=config.user_search_base,
        user_search_filter=config.user_search_filter,
        use_tls=config.use_tls,
        tls_verify=config.tls_verify,
        tls_ca_bundle_path=config.tls_ca_bundle_path,
        enabled=config.enabled,
        bind_dn=config.bind_dn or None,
        has_bind_password=_config_has_credentials(config),
    )


@router.post("/api/settings/ldap", response_model=LdapConfigResponse)
async def update_ldap_config(config_request: LdapConfigRequest, admin: KhojUser = Depends(require_admin)):
    """Update LDAP configuration (admin only)."""
    _maybe_update_bind_credentials(config_request.bind_dn, config_request.bind_password)

    # Build update defaults (non-credential fields)
    defaults = {
        "server_url": config_request.server_url,
        "user_search_base": config_request.user_search_base,
        "user_search_filter": config_request.user_search_filter,
        "use_tls": config_request.use_tls,
        "tls_verify": config_request.tls_verify,
        "tls_ca_bundle_path": config_request.tls_ca_bundle_path,
        "enabled": config_request.enabled,
    }

    # Save bind_dn if provided
    bind_dn = (config_request.bind_dn or "").strip() or None
    if bind_dn:
        defaults["bind_dn"] = bind_dn

    # Determine whether credentials will be available after this save
    bind_password = (config_request.bind_password or "").strip()
    # For the enabled check, we look at what credentials will exist:
    # - new credentials from the request (bind_dn + bind_password), OR
    # - existing DB credentials (if we're not clearing them), OR
    # - env vars / Vault
    new_db_creds = bool(bind_dn and bind_password)
    will_have_creds = new_db_creds or is_vault_configured() or has_ldap_credentials()

    if not will_have_creds:
        # Check if existing DB record already has credentials
        existing = await LdapConfig.objects.filter().afirst()
        if existing and _config_has_credentials(existing):
            will_have_creds = True

    if config_request.enabled and not will_have_creds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "LDAP credentials not configured. Provide bind_dn and bind_password in settings, "
                "set KHOJ_LDAP_BIND_DN and KHOJ_LDAP_BIND_PASSWORD environment variables, or configure Vault."
            ),
        )

    config, created = await LdapConfig.objects.aupdate_or_create(defaults=defaults)

    # Encrypt and persist the bind password when provided
    if bind_password:
        await sync_to_async(config.set_bind_password)(bind_password)
        await config.asave(update_fields=["bind_password_enc"])

    logger.info(f"LDAP configuration {'created' if created else 'updated'} by {admin.username}")

    return LdapConfigResponse(
        server_url=config.server_url,
        user_search_base=config.user_search_base,
        user_search_filter=config.user_search_filter,
        use_tls=config.use_tls,
        tls_verify=config.tls_verify,
        tls_ca_bundle_path=config.tls_ca_bundle_path,
        enabled=config.enabled,
        bind_dn=config.bind_dn or None,
        has_bind_password=_config_has_credentials(config),
    )


@router.post("/api/settings/ldap/test", response_model=LdapTestResponse)
async def test_ldap_connection(test_request: LdapTestRequest, admin: KhojUser = Depends(require_admin)):
    """Test LDAP connection without saving configuration (admin only)."""
    try:
        _maybe_update_bind_credentials(test_request.bind_dn, test_request.bind_password)

        # Build a temporary config to test against
        temp_config = LdapConfig(
            server_url=test_request.server_url,
            user_search_base=test_request.user_search_base,
            user_search_filter=test_request.user_search_filter,
            use_tls=test_request.use_tls,
            tls_verify=test_request.tls_verify,
            tls_ca_bundle_path=test_request.tls_ca_bundle_path,
            enabled=True,
        )

        # Attach in-form credentials to the temporary config if provided
        bind_dn = (test_request.bind_dn or "").strip()
        bind_password = (test_request.bind_password or "").strip()
        if bind_dn:
            temp_config.bind_dn = bind_dn
        if bind_password:
            temp_config.set_bind_password(bind_password)

        # Fall back to DB-stored config for credentials when not supplied inline
        if not _config_has_credentials(temp_config):
            existing = await LdapConfig.objects.filter().afirst()
            if existing and _config_has_credentials(existing):
                temp_config.bind_dn = existing.bind_dn
                temp_config.bind_password_enc = existing.bind_password_enc

        if not _config_has_credentials(temp_config) and not is_vault_configured() and not has_ldap_credentials():
            return LdapTestResponse(
                success=False,
                message=(
                    "LDAP credentials not configured. Provide bind_dn and bind_password in the form, "
                    "set KHOJ_LDAP_BIND_DN and KHOJ_LDAP_BIND_PASSWORD environment variables, or configure Vault."
                ),
            )

        backend = await sync_to_async(LdapAuthBackend)(temp_config)
        success, message = await sync_to_async(backend.test_connection)()

        return LdapTestResponse(success=success, message=message)

    except LdapAuthError as e:
        return LdapTestResponse(success=False, message=str(e))
    except Exception:
        logger.exception("LDAP connection test failed")
        return LdapTestResponse(success=False, message="Connection test failed. Check logs for details.")


@router.get("/api/settings/ldap/users", response_model=list[LdapManagedUser])
async def list_ldap_users(admin: KhojUser = Depends(require_admin)):
    """List LDAP-linked user accounts for admin management."""

    users_query = (
        KhojUser.objects.exclude(ldap_dn__isnull=True)
        .exclude(ldap_dn__exact="")
        .order_by("username")
        .values("id", "username", "email", "first_name", "last_name", "ldap_dn", "is_active", "is_staff", "is_superuser")
    )
    rows = await sync_to_async(list)(users_query)

    return [
        LdapManagedUser(
            id=row["id"],
            username=row["username"],
            email=row.get("email") or "",
            first_name=row.get("first_name") or "",
            last_name=row.get("last_name") or "",
            ldap_dn=row["ldap_dn"],
            is_active=bool(row["is_active"]),
            is_admin=bool(row["is_staff"] or row["is_superuser"]),
        )
        for row in rows
    ]


@router.patch("/api/settings/ldap/users/{user_id}", response_model=LdapManagedUser)
async def update_ldap_user(user_id: int, update_request: LdapUserUpdateRequest, admin: KhojUser = Depends(require_admin)):
    """Update LDAP-managed user status/permissions."""

    if update_request.is_active is None and update_request.is_admin is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")

    user = await KhojUser.objects.filter(id=user_id).afirst()
    if not user or not user.ldap_dn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LDAP user not found")

    if update_request.is_admin is not None:
        user.is_staff = bool(update_request.is_admin)
    if update_request.is_active is not None:
        user.is_active = bool(update_request.is_active)

    await user.asave(update_fields=["is_staff", "is_active", "updated_at"])

    return LdapManagedUser(
        id=user.id,
        username=user.username,
        email=user.email or "",
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        ldap_dn=user.ldap_dn,
        is_active=user.is_active,
        is_admin=bool(user.is_staff or user.is_superuser),
    )


@router.post("/auth/ldap/login", response_model=LdapLoginResponse)
async def ldap_login(request: Request, login_request: LdapLoginRequest):
    """Authenticate user via LDAP.

    Rate limited to 5 attempts per IP per minute and 10 per username per minute.
    """
    client_ip = request.client.host if request.client else "unknown"
    username = login_request.username

    ip_allowed = _check_rate_limit(f"ip:{client_ip}", max_attempts=5, window=60)
    user_allowed = _check_rate_limit(f"user:{username}", max_attempts=10, window=60)

    if not ip_allowed or not user_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": "60"},
        )

    try:
        from khoj.configure import UserAuthenticationBackend

        auth_backend = UserAuthenticationBackend()
        user = await auth_backend.authenticate_ldap(username=username, password=login_request.password)

        if not user:
            return LdapLoginResponse(success=False, message="Invalid credentials")

        request.session["user"] = {"email": user.email}

        return LdapLoginResponse(success=True, message="Authentication successful", user_id=str(user.uuid))

    except LdapAuthError as e:
        logger.warning(f"LDAP authentication error for {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LDAP authentication service unavailable",
        )
    except Exception:
        logger.exception("LDAP login failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication failed")
