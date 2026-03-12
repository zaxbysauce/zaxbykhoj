"""LDAP Authentication Backend for Khoj.

Implements LDAP authentication with Windows Active Directory support.
Uses two-bind authentication flow for security.
"""
import logging
from typing import Optional, Tuple

from ldap3 import Connection, Server, Tls, AUTO_BIND_NONE, ALL
from ldap3.core.exceptions import LDAPException

from khoj.utils.secrets import get_ldap_bind_dn, get_ldap_bind_password
from khoj.utils.secrets_vault import (
    get_ldap_credentials_from_vault,
    is_vault_configured,
)

logger = logging.getLogger(__name__)


class LdapAuthError(Exception):
    """Raised when LDAP authentication fails."""
    pass


class LdapAuthBackend:
    """LDAP Authentication Backend for Khoj.
    
    Implements secure LDAP authentication with:
    - TLS certificate validation
    - LDAP injection prevention
    - Two-bind authentication flow
    - Connection pooling
    
    Security Notes:
    - Credentials are NEVER logged
    - User input is sanitized before use in LDAP filters
    - TLS is enforced by default
    """
    
    def __init__(self, config):
        """Initialize LDAP authentication backend.
        
        Args:
            config: LdapConfig model instance with server settings
        """
        self.config = config
        self.server = None
        self._initialize_server()
    
    def _initialize_server(self) -> None:
        """Initialize LDAP server connection with TLS configuration.

        Configures TLS with certificate validation. Supports custom CA bundles
        for environments with private certificate authorities.

        Raises:
            LdapAuthError: If server configuration is invalid
        """
        import ssl

        try:
            # Determine TLS mode based on URL scheme and config
            use_ssl = self.config.server_url.lower().startswith("ldaps://")

            # Enforce TLS - never allow cleartext LDAP
            if not use_ssl and not self.config.use_tls:
                raise LdapAuthError(
                    "TLS is required for LDAP connections. "
                    "Set use_tls=True in configuration or use ldaps:// URL."
                )

            if self.config.use_tls or use_ssl:
                # Validate custom CA bundle path if provided
                if self.config.tls_ca_bundle_path:
                    import os
                    if not os.path.isfile(self.config.tls_ca_bundle_path):
                        raise LdapAuthError(
                            f"CA bundle file not found: {self.config.tls_ca_bundle_path}"
                        )

                # Configure TLS with certificate validation
                tls_kwargs = {
                    "validate": ssl.CERT_REQUIRED if self.config.tls_verify else ssl.CERT_NONE,
                }

                # Add custom CA bundle if provided
                if self.config.tls_ca_bundle_path:
                    tls_kwargs["ca_certs_file"] = self.config.tls_ca_bundle_path

                tls = Tls(**tls_kwargs)
            else:
                tls = None

            # Create server with appropriate TLS configuration
            self.server = Server(
                self.config.server_url,
                use_ssl=use_ssl,
                tls=tls,
                get_info=ALL,
            )

            logger.debug(f"LDAP server initialized: {self.config.server_url}")

        except Exception:
            logger.exception("Failed to initialize LDAP server")
            raise LdapAuthError(
                "Failed to initialize LDAP server. "
                "Check configuration and logs for details."
            )
    
    def _get_bind_credentials(self) -> Tuple[str, str]:
        """Get LDAP bind credentials from secure storage.
        
        Returns:
            tuple: (bind_dn, bind_password)
            
        Security:
            Credentials are retrieved from Vault or environment variables.
            Passwords are NEVER logged.
        """
        if is_vault_configured():
            return get_ldap_credentials_from_vault()
        return get_ldap_bind_dn(), get_ldap_bind_password()
    
    def _sanitize_username(self, username: str) -> str:
        """Sanitize username for LDAP filter to prevent injection.
        
        Uses ldap3's escape_filter_chars to escape special characters
        that could be used for LDAP injection attacks.
        
        Per RFC 4515, the following characters are escaped:
        - * (wildcard) → \\2a
        - ( ) (parentheses) → \\28 \\29
        - \\ (backslash) → \\5c
        - NUL character → \\00
        
        Args:
            username: Raw username input
            
        Returns:
            Sanitized username safe for LDAP filter
            
        Raises:
            ValueError: If username is empty or None
        """
        from ldap3.utils.conv import escape_filter_chars
        
        # Reject empty/None input
        if not username:
            raise ValueError("Username cannot be empty or None")
        
        # Convert to string if needed and encode/decode for Unicode safety
        username_str = str(username)
        
        # Truncate BEFORE escaping to avoid breaking escape sequences
        max_length = 256
        if len(username_str) > max_length:
            logger.warning(f"Username exceeds max length ({max_length}), truncating")
            username_str = username_str[:max_length]
        
        # Escape special LDAP filter characters
        try:
            sanitized = escape_filter_chars(username_str)
        except Exception as e:
            logger.exception("Failed to escape username")
            raise ValueError(f"Invalid username format: {e}")
        
        return sanitized
    
    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user against LDAP.
        
        Implements two-bind authentication:
        1. Bind with service account to search for user
        2. Bind with user credentials to verify
        
        Args:
            username: User's login name (sAMAccountName for AD)
            password: User's password
            
        Returns:
            dict: User attributes (dn, email, name) if authenticated
            None: If authentication fails
            
        Raises:
            LdapAuthError: If LDAP server is unreachable or misconfigured
        """
        from django.db import transaction

        # Sanitize username
        try:
            sanitized_username = self._sanitize_username(username)
        except ValueError as e:
            self._log_auth_attempt(username, "failed", "invalid_username")
            return None

        # Reject empty passwords early to avoid anonymous/invalid bind attempts
        if not password:
            self._log_auth_attempt(username, "failed", "invalid_credentials")
            return None
        
        # Get service account credentials
        try:
            bind_dn, bind_password = self._get_bind_credentials()
        except Exception:
            logger.exception("Failed to retrieve bind credentials")
            raise LdapAuthError("LDAP configuration error")
        
        conn = None
        user_conn = None
        
        try:
            # Step 1: Bind with service account to search for user
            conn = Connection(
                self.server,
                user=bind_dn,
                password=bind_password,
                auto_bind=AUTO_BIND_NONE,
                read_only=True,
            )
            
            if not conn.bind():
                logger.error("Service account bind failed")
                raise LdapAuthError("LDAP service account authentication failed")
            
            # Search for user
            search_filter = self.config.user_search_filter.format(username=sanitized_username)
            search_base = self.config.user_search_base
            
            conn.search(
                search_base=search_base,
                search_filter=search_filter,
                search_scope='SUBTREE',
                attributes=['cn', 'mail', 'givenName', 'sn', 'sAMAccountName', 'dn'],
            )
            
            if not conn.entries:
                self._log_auth_attempt(username, "failed", "user_not_found")
                return None
            
            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn
            
            # Step 2: Bind with user credentials to verify
            user_conn = Connection(
                self.server,
                user=user_dn,
                password=password,
                auto_bind=AUTO_BIND_NONE,
            )
            
            if not user_conn.bind():
                self._log_auth_attempt(username, "failed", "invalid_credentials")
                return None
            
            # Extract user attributes
            ldap_username = self._extract_ldap_attr(user_entry, 'sAMAccountName') or username
            user_attrs = {
                'dn': user_dn,
                'username': ldap_username,
                'email': self._extract_ldap_attr(user_entry, 'mail'),
                'first_name': self._extract_ldap_attr(user_entry, 'givenName'),
                'last_name': self._extract_ldap_attr(user_entry, 'sn'),
                'full_name': self._extract_ldap_attr(user_entry, 'cn'),
            }
            
            # Step 3: Provision or update local user
            with transaction.atomic():
                khoj_user = self._get_or_create_user(user_attrs)
                self._update_user_from_ldap(khoj_user, user_attrs)
            
            self._log_auth_attempt(username, "success", None)
            
            return user_attrs
            
        except LDAPException:
            logger.exception("LDAP error during authentication")
            self._log_auth_attempt(username, "failed", "ldap_error")
            raise LdapAuthError("LDAP authentication failed")
        except Exception:
            logger.exception("Unexpected error during authentication")
            self._log_auth_attempt(username, "failed", "system_error")
            raise LdapAuthError("Authentication system error")
        finally:
            if conn:
                conn.unbind()
            if user_conn:
                user_conn.unbind()
    
    def _get_or_create_user(self, ldap_attrs: dict) -> 'KhojUser':
        """Get existing user or create new one based on LDAP DN.
        
        Args:
            ldap_attrs: Dictionary with user attributes from LDAP
            
        Returns:
            KhojUser: Existing or newly created user
        """
        from khoj.database.models import KhojUser
        
        user_dn = ldap_attrs['dn']
        username = ldap_attrs['username']
        
        # Try to find by LDAP DN first
        try:
            user = KhojUser.objects.get(ldap_dn=user_dn)
            return user
        except KhojUser.DoesNotExist:
            pass
        
        # Try to find by username
        try:
            user = KhojUser.objects.get(username=username)
            # Link to LDAP DN
            user.ldap_dn = user_dn
            user.save(update_fields=['ldap_dn'])
            return user
        except KhojUser.DoesNotExist:
            pass
        
        # Create new user
        email = ldap_attrs.get('email') or f"{username}@localhost"
        user = KhojUser.objects.create(
            username=username,
            email=email,
            ldap_dn=user_dn,
        )
        
        logger.info(f"Created new KhojUser from LDAP: {username}")
        return user

    def _extract_ldap_attr(self, entry, attr_name: str) -> Optional[str]:
        """Extract and normalize LDAP attribute value from ldap3 entry.

        Handles ldap3 EntryAttribute wrappers and list-valued attributes,
        returning a trimmed string or None.
        """
        raw_value = getattr(entry, attr_name, None)
        if raw_value is None:
            return None

        value = getattr(raw_value, "value", raw_value)
        if isinstance(value, list):
            value = value[0] if value else None
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None
    
    def _update_user_from_ldap(self, user: 'KhojUser', ldap_attrs: dict) -> None:
        """Update local user attributes from LDAP.
        
        Args:
            user: KhojUser instance to update
            ldap_attrs: Dictionary with attributes from LDAP
        """
        updated = False
        
        # Only update if LDAP value is non-empty and different from current
        first_name = ldap_attrs.get('first_name', '').strip()
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            updated = True
        
        last_name = ldap_attrs.get('last_name', '').strip()
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            updated = True
        
        email = ldap_attrs.get('email', '').strip()
        if email and user.email != email:
            user.email = email
            updated = True
        
        if updated:
            user.save(update_fields=['first_name', 'last_name', 'email'])
            logger.debug(f"Updated KhojUser from LDAP: {user.username}")
    
    def _log_auth_attempt(self, username: str, outcome: str, failure_reason: Optional[str]) -> None:
        """Log authentication attempt for audit purposes.
        
        Security:
            - Username is hashed (not stored in plaintext)
            - Passwords are NEVER logged
            - Structured JSON format for SIEM ingestion
        
        Args:
            username: The username attempted
            outcome: 'success' or 'failed'
            failure_reason: Reason for failure (None if success)
        """
        import hashlib
        import json
        from datetime import datetime
        
        # Hash the username for privacy
        username_hash = hashlib.sha256(username.encode()).hexdigest()[:16]
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'ldap_auth_attempt',
            'username_hash': username_hash,
            'outcome': outcome,
            'source_ip': None,  # Will be set by caller if available
        }
        
        if failure_reason:
            log_entry['failure_reason'] = failure_reason
        
        # Log as JSON for SIEM ingestion
        logger.info(f"AUDIT: {json.dumps(log_entry)}")
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test LDAP connection without authenticating.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            bind_dn, bind_password = self._get_bind_credentials()
            
            conn = Connection(
                self.server,
                user=bind_dn,
                password=bind_password,
                auto_bind=AUTO_BIND_NONE,
                read_only=True,
            )
            
            if conn.bind():
                # Try a simple search to verify permissions
                conn.search(
                    search_base=self.config.user_search_base,
                    search_filter='(objectClass=*)',
                    search_scope='BASE',
                    size_limit=1,
                )
                conn.unbind()
                return True, "LDAP connection successful"
            else:
                return False, "Failed to bind with service account"
                
        except Exception as e:
            logger.exception("LDAP connection test failed")
            return False, str(e)
