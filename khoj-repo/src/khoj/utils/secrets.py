"""Secret management for LDAP and other sensitive configuration.

Credentials can be stored in the database (Fernet-encrypted) or supplied via
environment variables.  Database-stored credentials take priority over env vars
so that settings configured through the admin UI persist across restarts.
"""
import base64
import hashlib
import os
import logging

logger = logging.getLogger(__name__)


class LdapSecretError(Exception):
    """Raised when LDAP secrets cannot be retrieved."""
    pass


def _fernet_key() -> bytes:
    """Derive a URL-safe base64-encoded 32-byte key from Django's SECRET_KEY."""
    from django.conf import settings
    raw = settings.SECRET_KEY.encode()
    return base64.urlsafe_b64encode(hashlib.sha256(raw).digest())


def encrypt_ldap_password(plaintext: str) -> str:
    """Encrypt *plaintext* with Fernet and return the token as a string."""
    from cryptography.fernet import Fernet
    f = Fernet(_fernet_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt_ldap_password(token: str) -> str:
    """Decrypt a Fernet token produced by :func:`encrypt_ldap_password`."""
    from cryptography.fernet import Fernet, InvalidToken
    if not token:
        raise LdapSecretError("No encrypted LDAP bind password stored in database.")
    try:
        f = Fernet(_fernet_key())
        return f.decrypt(token.encode()).decode()
    except InvalidToken:
        raise LdapSecretError(
            "Failed to decrypt LDAP bind password — SECRET_KEY may have changed."
        )


def get_ldap_bind_dn() -> str:
    """Get LDAP bind DN from environment variable.
    
    Returns:
        str: The bind DN (e.g., "CN=service,DC=example,DC=com")
        
    Raises:
        LdapSecretError: If KHOJ_LDAP_BIND_DN is not set
    """
    bind_dn = os.getenv("KHOJ_LDAP_BIND_DN")
    if not bind_dn:
        raise LdapSecretError(
            "KHOJ_LDAP_BIND_DN environment variable not set. "
            "Set it to the LDAP service account DN."
        )
    return bind_dn


def get_ldap_bind_password() -> str:
    """Get LDAP bind password from environment variable.
    
    Returns:
        str: The bind password
        
    Raises:
        LdapSecretError: If KHOJ_LDAP_BIND_PASSWORD is not set
        
    Security:
        Password is NEVER logged.
    """
    password = os.getenv("KHOJ_LDAP_BIND_PASSWORD")
    if not password:
        raise LdapSecretError(
            "KHOJ_LDAP_BIND_PASSWORD environment variable not set. "
            "Set it to the LDAP service account password."
        )
    return password


def get_ldap_credentials() -> tuple[str, str]:
    """Get both LDAP bind DN and password.
    
    Returns:
        tuple: (bind_dn, bind_password)
        
    Raises:
        LdapSecretError: If either credential is not set
    """
    return get_ldap_bind_dn(), get_ldap_bind_password()


def set_ldap_credentials(bind_dn: str, bind_password: str) -> None:
    """Set LDAP bind credentials in process environment.

    This enables runtime updates from the admin settings page without logging
    or persisting passwords in the database.
    """
    bind_dn = (bind_dn or "").strip()
    bind_password = (bind_password or "").strip()

    if not bind_dn:
        raise LdapSecretError("LDAP bind DN cannot be empty")
    if not bind_password:
        raise LdapSecretError("LDAP bind password cannot be empty")

    os.environ["KHOJ_LDAP_BIND_DN"] = bind_dn
    os.environ["KHOJ_LDAP_BIND_PASSWORD"] = bind_password


def has_ldap_credentials() -> bool:
    """Check if LDAP credentials are configured.
    
    Returns:
        bool: True if both KHOJ_LDAP_BIND_DN and KHOJ_LDAP_BIND_PASSWORD are set
    """
    return bool(
        os.getenv("KHOJ_LDAP_BIND_DN") and 
        os.getenv("KHOJ_LDAP_BIND_PASSWORD")
    )
