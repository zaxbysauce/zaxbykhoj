"""LDAP Configuration and Authentication API Router."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from khoj.database.models import KhojUser, LdapConfig
from khoj.processor.auth import LdapAuthBackend, LdapAuthError
from khoj.utils.secrets import get_ldap_bind_dn, has_ldap_credentials
from khoj.utils.secrets_vault import is_vault_configured

logger = logging.getLogger(__name__)

router = APIRouter(tags=["LDAP"])


# Pydantic models for request/response
class LdapConfigResponse(BaseModel):
    """LDAP configuration response (passwords excluded)."""
    server_url: str
    user_search_base: str
    user_search_filter: str
    use_tls: bool
    tls_verify: bool
    tls_ca_bundle_path: Optional[str] = None
    enabled: bool


class LdapConfigRequest(BaseModel):
    """LDAP configuration request."""
    server_url: str = Field(..., description="LDAP server URL (e.g., ldaps://ad.company.com:636)")
    user_search_base: str = Field(..., description="Base DN for user searches")
    user_search_filter: str = Field(default="(sAMAccountName={username})", description="Search filter template")
    use_tls: bool = Field(default=True, description="Use TLS/SSL")
    tls_verify: bool = Field(default=True, description="Verify TLS certificates")
    tls_ca_bundle_path: Optional[str] = Field(default=None, description="Path to custom CA bundle")
    enabled: bool = Field(default=False, description="Enable LDAP authentication")
    
    @validator('server_url')
    def validate_server_url(cls, v):
        if not v.startswith(('ldap://', 'ldaps://')):
            raise ValueError('server_url must start with ldap:// or ldaps://')
        return v


class LdapTestRequest(BaseModel):
    """LDAP connection test request."""
    server_url: str
    user_search_base: str
    user_search_filter: str = "(sAMAccountName={username})"
    use_tls: bool = True
    tls_verify: bool = True
    tls_ca_bundle_path: Optional[str] = None


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


# Rate limiting storage (in production, use Redis)
_auth_attempts = {}


def _check_rate_limit(identifier: str, max_attempts: int = 5, window: int = 60) -> bool:
    """Check if request is within rate limit.
    
    Args:
        identifier: IP address or username
        max_attempts: Maximum allowed attempts
        window: Time window in seconds
        
    Returns:
        True if within limit, False if exceeded
    """
    import time
    from collections import deque
    
    now = time.time()
    
    if identifier not in _auth_attempts:
        _auth_attempts[identifier] = deque()
    
    # Remove old entries
    attempts = _auth_attempts[identifier]
    while attempts and attempts[0] < now - window:
        attempts.popleft()
    
    # Check limit
    if len(attempts) >= max_attempts:
        return False
    
    # Record attempt
    attempts.append(now)
    return True


def get_current_user(request: Request) -> KhojUser:
    """Get the authenticated Django user from the request.
    
    Raises HTTP 401 if user is not authenticated.
    """
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


@router.get("/api/settings/ldap", response_model=LdapConfigResponse)
async def get_ldap_config(admin: KhojUser = Depends(require_admin)):
    """Get current LDAP configuration (admin only).
    
    Returns LDAP configuration without exposing passwords.
    """
    config = await LdapConfig.objects.filter().afirst()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LDAP configuration not found"
        )
    
    return LdapConfigResponse(
        server_url=config.server_url,
        user_search_base=config.user_search_base,
        user_search_filter=config.user_search_filter,
        use_tls=config.use_tls,
        tls_verify=config.tls_verify,
        tls_ca_bundle_path=config.tls_ca_bundle_path,
        enabled=config.enabled,
    )


@router.post("/api/settings/ldap", response_model=LdapConfigResponse)
async def update_ldap_config(
    config_request: LdapConfigRequest,
    admin: KhojUser = Depends(require_admin)
):
    """Update LDAP configuration (admin only).
    
    Saves LDAP configuration. Credentials must be set via environment
    variables (KHOJ_LDAP_BIND_DN, KHOJ_LDAP_BIND_PASSWORD) or Vault.
    """
    # Validate credentials are configured
    if config_request.enabled:
        if not is_vault_configured() and not has_ldap_credentials():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LDAP credentials not configured. Set KHOJ_LDAP_BIND_DN and "
                       "KHOJ_LDAP_BIND_PASSWORD environment variables, or configure Vault."
            )
    
    # Update or create config
    config, created = await LdapConfig.objects.aupdate_or_create(
        defaults={
            'server_url': config_request.server_url,
            'user_search_base': config_request.user_search_base,
            'user_search_filter': config_request.user_search_filter,
            'use_tls': config_request.use_tls,
            'tls_verify': config_request.tls_verify,
            'tls_ca_bundle_path': config_request.tls_ca_bundle_path,
            'enabled': config_request.enabled,
        }
    )
    
    logger.info(f"LDAP configuration {'created' if created else 'updated'} by {admin.username}")
    
    return LdapConfigResponse(
        server_url=config.server_url,
        user_search_base=config.user_search_base,
        user_search_filter=config.user_search_filter,
        use_tls=config.use_tls,
        tls_verify=config.tls_verify,
        tls_ca_bundle_path=config.tls_ca_bundle_path,
        enabled=config.enabled,
    )


@router.post("/api/settings/ldap/test", response_model=LdapTestResponse)
async def test_ldap_connection(
    test_request: LdapTestRequest,
    admin: KhojUser = Depends(require_admin)
):
    """Test LDAP connection without saving configuration (admin only).
    
    Tests connectivity to LDAP server with provided settings.
    """
    try:
        # Check credentials are available
        if not is_vault_configured() and not has_ldap_credentials():
            return LdapTestResponse(
                success=False,
                message="LDAP credentials not configured. Set KHOJ_LDAP_BIND_DN and "
                        "KHOJ_LDAP_BIND_PASSWORD environment variables, or configure Vault."
            )
        
        # Create temporary config
        temp_config = LdapConfig(
            server_url=test_request.server_url,
            user_search_base=test_request.user_search_base,
            user_search_filter=test_request.user_search_filter,
            use_tls=test_request.use_tls,
            tls_verify=test_request.tls_verify,
            tls_ca_bundle_path=test_request.tls_ca_bundle_path,
            enabled=True,
        )
        
        # Test connection
        backend = LdapAuthBackend(temp_config)
        success, message = backend.test_connection()
        
        return LdapTestResponse(success=success, message=message)
        
    except LdapAuthError as e:
        return LdapTestResponse(success=False, message=str(e))
    except Exception as e:
        logger.exception("LDAP connection test failed")
        return LdapTestResponse(
            success=False,
            message="Connection test failed. Check logs for details."
        )


@router.post("/auth/ldap/login", response_model=LdapLoginResponse)
async def ldap_login(
    request: Request,
    login_request: LdapLoginRequest
):
    """Authenticate user via LDAP.
    
    Rate limited to 5 attempts per IP per minute and 10 per username per minute.
    """
    client_ip = request.client.host if request.client else "unknown"
    username = login_request.username
    
    # Check rate limits
    ip_allowed = _check_rate_limit(f"ip:{client_ip}", max_attempts=5, window=60)
    user_allowed = _check_rate_limit(f"user:{username}", max_attempts=10, window=60)
    
    if not ip_allowed or not user_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": "60"}
        )
    
    try:
        from khoj.configure import UserAuthenticationBackend
        
        auth_backend = UserAuthenticationBackend()
        user = await auth_backend.authenticate_ldap(
            username=username,
            password=login_request.password
        )
        
        if not user:
            return LdapLoginResponse(
                success=False,
                message="Invalid credentials"
            )
        
        # Create session
        request.session["user"] = {"email": user.email}
        
        return LdapLoginResponse(
            success=True,
            message="Authentication successful",
            user_id=str(user.uuid)
        )
        
    except LdapAuthError as e:
        logger.warning(f"LDAP authentication error for {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LDAP authentication service unavailable"
        )
    except Exception as e:
        logger.exception("LDAP login failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )
