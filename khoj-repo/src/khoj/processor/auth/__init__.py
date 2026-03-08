"""LDAP Authentication Backend for Khoj.

This module provides LDAP authentication support with:
- TLS/SSL certificate validation
- LDAP injection prevention
- Two-bind authentication flow
- User provisioning from LDAP
"""

from .ldap_backend import LdapAuthBackend, LdapAuthError

__all__ = ["LdapAuthBackend", "LdapAuthError"]
