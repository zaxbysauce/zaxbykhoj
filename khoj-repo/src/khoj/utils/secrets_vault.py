"""HashiCorp Vault adapter for secret retrieval.

Supports KV v2 secret engine for LDAP credentials.
Credentials are cached with TTL to reduce Vault API calls.
"""
import os
import time
import logging
from typing import Optional, Tuple

try:
    import hvac
    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False

from .secrets import LdapSecretError

logger = logging.getLogger(__name__)


class VaultAdapter:
    """Adapter for retrieving secrets from HashiCorp Vault."""
    
    def __init__(self):
        self.client: Optional[hvac.Client] = None
        self._cache: dict = {}
        self._cache_timestamp: float = 0
        self._cache_ttl: int = int(os.getenv("KHOJ_VAULT_CACHE_TTL", "300"))
        
        if not HVAC_AVAILABLE:
            raise LdapSecretError(
                "HashiCorp Vault support requires 'hvac' package. "
                "Install with: pip install hvac"
            )
        
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize Vault client from environment variables."""
        vault_addr = os.getenv("KHOJ_VAULT_ADDR")
        vault_token = os.getenv("KHOJ_VAULT_TOKEN")
        
        if not vault_addr or not vault_token:
            raise LdapSecretError(
                "Vault configuration incomplete. Set KHOJ_VAULT_ADDR and KHOJ_VAULT_TOKEN."
            )
        
        try:
            self.client = hvac.Client(url=vault_addr, token=vault_token)
        except Exception:
            logger.exception("Failed to connect to Vault")
            raise LdapSecretError("Failed to connect to Vault. Check configuration and logs.")
        
        if not self.client.is_authenticated():
            raise LdapSecretError("Vault token authentication failed")
    
    def _get_cache_key(self) -> str:
        """Generate cache key from Vault path."""
        return os.getenv("KHOJ_VAULT_PATH", "secret/data/khoj/ldap")
    
    def _is_cache_valid(self) -> bool:
        """Check if cached credentials are still valid."""
        if not self._cache:
            return False
        return (time.time() - self._cache_timestamp) < self._cache_ttl
    
    def _read_from_vault(self) -> dict:
        """Read secrets from Vault KV v2."""
        path = self._get_cache_key()
        
        try:
            # Parse KV v2 path (format: secret/data/path)
            mount_point, _, secret_path = path.partition("/data/")
            if not secret_path:
                # Try without data/ prefix
                mount_point = path.split("/")[0]
                secret_path = "/".join(path.split("/")[1:])
            
            response = self.client.secrets.kv.v2.read_secret_version(
                path=secret_path,
                mount_point=mount_point
            )
            
            return response["data"]["data"]
        except Exception:
            logger.exception("Failed to read from Vault")
            raise LdapSecretError("Failed to retrieve secrets from Vault. Check configuration and logs.")
    
    def get_ldap_credentials(self) -> Tuple[str, str]:
        """Get LDAP credentials from Vault with caching.
        
        Returns:
            tuple: (bind_dn, bind_password)
            
        Raises:
            LdapSecretError: If credentials cannot be retrieved
        """
        if self._is_cache_valid():
            logger.debug("Returning cached LDAP credentials")
            data = self._cache
        else:
            logger.debug("Fetching LDAP credentials from Vault")
            data = self._read_from_vault()
            self._cache = data
            self._cache_timestamp = time.time()
        
        bind_dn = data.get("bind_dn")
        bind_password = data.get("bind_password")
        
        if not bind_dn or not bind_password:
            raise LdapSecretError(
                "Vault secret missing required fields: bind_dn, bind_password"
            )
        
        return bind_dn, bind_password
    
    def clear_cache(self) -> None:
        """Clear the credential cache."""
        self._cache = {}
        self._cache_timestamp = 0
        logger.debug("Vault credential cache cleared")


def get_ldap_credentials_from_vault() -> Tuple[str, str]:
    """Convenience function to get LDAP credentials from Vault.
    
    Returns:
        tuple: (bind_dn, bind_password)
        
    Raises:
        LdapSecretError: If Vault is not configured or credentials unavailable
    """
    adapter = VaultAdapter()
    return adapter.get_ldap_credentials()


def is_vault_configured() -> bool:
    """Check if Vault is configured for LDAP credentials.
    
    Returns:
        bool: True if all required Vault env vars are set
    """
    required = ["KHOJ_VAULT_ADDR", "KHOJ_VAULT_TOKEN", "KHOJ_VAULT_PATH"]
    return all(os.getenv(var) for var in required)
