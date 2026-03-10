<!-- PLAN_HASH: 3cdvzoygc1ul4 -->
# Khoj Authentication Enhancement
Swarm: khoj-auth-enhancement-2026
Phase: 1 [PENDING] | Updated: 2026-03-08T12:32:10.789Z

---
## Phase 1: Auth Disabled by Default [PENDING]
- [ ] 1.1: Change anonymous_mode default from False to True in src/khoj/utils/state.py [SMALL]
- [ ] 1.2: Change --anonymous-mode default from False to True in src/khoj/utils/cli.py and add --no-anonymous-mode flag [SMALL]
- [ ] 1.3: Update documentation/docs/advanced/authentication.mdx [MEDIUM] ← CURRENT
- [ ] 1.4: Create tests/test_anonymous_mode_default.py [MEDIUM]
- [ ] 1.5: Document migration steps for existing deployments [MEDIUM]
- [ ] 1.6: Document rollback procedure [SMALL]

---
## Phase 2: LDAP Dependencies and Secret Management [PENDING]
- [ ] 2.1: Add ldap3>=2.9.1 to pyproject.toml [SMALL]
- [ ] 2.2: Create src/khoj/utils/secrets.py [MEDIUM]
- [ ] 2.3: Add HashiCorp Vault adapter in src/khoj/utils/secrets_vault.py [MEDIUM] (depends: 2.2)
- [ ] 2.4: Verify NO password fields in LdapConfig database model [SMALL]

---
## Phase 3: LDAP Database Models [PENDING]
- [ ] 3.1: Create Django migration 0103_add_ldap_dn_to_user [SMALL]
- [ ] 3.2: Create Django migration 0104_ldap_config [SMALL] (depends: 3.1)
- [ ] 3.3: Implement LdapConfig model [MEDIUM] (depends: 3.2)
- [ ] 3.4: Add ldap_dn field to KhojUser [SMALL] (depends: 3.1)
- [ ] 3.5: Register LdapConfig in Django admin [SMALL] (depends: 3.3)

---
## Phase 4: LDAP Authentication Backend - Part 1 [PENDING]
- [ ] 4.1: Create src/khoj/processor/auth/__init__.py [SMALL]
- [ ] 4.2: Create LdapAuthBackend class structure [MEDIUM] (depends: 3.3, 4.1)
- [ ] 4.3: Implement LDAP TLS configuration [MEDIUM] (depends: 4.2)
- [ ] 4.4: Implement LDAP injection prevention [MEDIUM] (depends: 4.2)

---
## Phase 5: LDAP Authentication Backend - Part 2 [PENDING]
- [ ] 5.1: Implement two-bind authentication flow [LARGE] (depends: 2.3, 4.3, 4.4)
- [ ] 5.2: Implement user provisioning [MEDIUM] (depends: 5.1)
- [ ] 5.3: Implement user sync [MEDIUM] (depends: 5.1)
- [ ] 5.4: Add audit logging [MEDIUM] (depends: 5.1)
- [ ] 5.5: Integrate into UserAuthenticationBackend [MEDIUM] (depends: 5.2, 5.3)

---
## Phase 6: LDAP API Endpoints [PENDING]
- [ ] 6.1: Create src/khoj/routers/ldap.py [SMALL]
- [ ] 6.2: GET /api/settings/ldap endpoint [MEDIUM] (depends: 3.3, 6.1)
- [ ] 6.3: POST /api/settings/ldap endpoint [MEDIUM] (depends: 6.2)
- [ ] 6.4: POST /api/settings/ldap/test endpoint [MEDIUM] (depends: 6.2)
- [ ] 6.5: Rate limiting for authentication [MEDIUM] (depends: 6.4)
- [ ] 6.6: POST /auth/ldap/login endpoint [MEDIUM] (depends: 5.5, 6.5)
- [ ] 6.7: Include ldap_router in configure.py [SMALL] (depends: 6.6)

---
## Phase 7: LDAP Settings UI [PENDING]
- [ ] 7.1: Create LdapConfigSection component [LARGE]
- [ ] 7.2: Validate UI accessibility [MEDIUM] (depends: 7.1)
- [ ] 7.3: Add LDAP section to settings page [MEDIUM] (depends: 6.3, 7.2)
- [ ] 7.4: Create LDAP login form [MEDIUM]
- [ ] 7.5: Integrate LDAP login into login page [MEDIUM] (depends: 6.6, 7.4)

---
## Phase 8: Testing, Security Review, and Documentation [PENDING]
- [ ] 8.1: Create tests/test_ldap_auth.py [LARGE] (depends: 5.5)
- [ ] 8.2: Create tests/test_ldap_config.py [MEDIUM] (depends: 6.3)
- [ ] 8.3: Create tests/test_anonymous_mode.py [MEDIUM] (depends: 1.4)
- [ ] 8.4: Security review [LARGE] (depends: 5.1, 6.6, 7.5)
- [ ] 8.5: Add LDAP documentation [MEDIUM]
- [ ] 8.6: Create integration test [LARGE] (depends: 6.7, 7.5)
- [ ] 8.7: Verify no email features in anonymous mode [MEDIUM] (depends: 1.1)
- [ ] 8.8: Performance test LDAP authentication [MEDIUM] (depends: 5.5)
