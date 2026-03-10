# Khoj Authentication Enhancement Specification
Version: 1.0 | Date: 2026-03-07

---

## Feature Overview

### FR-001: Authentication Disabled by Default
**MUST** Khoj deployments run without requiring authentication by default. When auth is disabled, the application operates in single-user mode with a default user context.

**Acceptance Criteria (SC-001):**
- GIVEN a fresh Khoj deployment
- WHEN started without explicit auth configuration
- THEN no login/signup screens are displayed
- AND all features are accessible without credentials

**Acceptance Criteria (SC-002):**
- GIVEN Khoj is running in anonymous mode
- WHEN accessing any protected endpoint
- THEN a default user context is automatically provided
- AND no redirect to login page occurs

### FR-002: Optional LDAP Authentication
**MUST** Administrators be able to enable LDAP authentication via configuration. When enabled, users authenticate against an external LDAP server.

**Acceptance Criteria (SC-003):**
- GIVEN LDAP is configured and enabled
- WHEN a user attempts to log in
- THEN credentials are validated against the LDAP server
- AND a local user record is created/updated upon successful auth

**Acceptance Criteria (SC-004):**
- GIVEN LDAP authentication is enabled
- WHEN LDAP server is unreachable
- THEN users receive a clear error message
- AND the system falls back gracefully (if fallback is configured)

### FR-003: Windows Active Directory Support
**MUST** The LDAP implementation support Windows Active Directory as the primary target.

**Acceptance Criteria (SC-005):**
- GIVEN an Active Directory server
- WHEN configuring LDAP with AD-specific settings (sAMAccountName, bind DN format)
- THEN authentication succeeds for valid AD users
- AND user attributes (name, email) are synchronized from AD

**Acceptance Criteria (SC-006):**
- GIVEN AD with nested groups
- WHEN a user belongs to authorized groups
- THEN group membership can be used for access control (optional feature)

### FR-004: LDAP Configuration UI
**MUST** Administrators be able to configure LDAP settings through the web interface.

**Acceptance Criteria (SC-007):**
- GIVEN admin access to Khoj
- WHEN navigating to settings
- THEN LDAP configuration section is visible
- AND all required fields can be edited (server URL, bind DN, search base, etc.)

**Acceptance Criteria (SC-008):**
- GIVEN LDAP configuration form is displayed
- WHEN clicking "Test Connection"
- THEN the system validates connectivity to the LDAP server
- AND displays success/failure status with clear error messages

**Acceptance Criteria (SC-009):**
- GIVEN LDAP settings are saved
- WHEN the configuration is invalid
- THEN the system prevents saving with validation errors
- AND does not break existing authentication

### FR-005: Seamless User Provisioning
**MUST** Users authenticating via LDAP be automatically provisioned in Khoj's local database.

**Acceptance Criteria (SC-010):**
- GIVEN a user successfully authenticates via LDAP for the first time
- WHEN the auth completes
- THEN a local KhojUser record is created
- AND the user is linked to their LDAP identity

**Acceptance Criteria (SC-011):**
- GIVEN a returning LDAP user
- WHEN they log in again
- THEN their existing local user record is updated
- AND their data/content remains associated with their account

### FR-006: No Email Dependencies in Anonymous Mode
**MUST** When running in anonymous/disabled auth mode, no email-related features or requirements are exposed.

**Acceptance Criteria (SC-012):**
- GIVEN anonymous mode is enabled
- WHEN viewing the application
- THEN no email signup/login options are displayed
- AND no email verification flows are required

**Acceptance Criteria (SC-013):**
- GIVEN anonymous mode is enabled
- WHEN a user accesses settings
- THEN email-related settings are hidden or disabled

---

## User Scenarios

### Scenario 1: Fresh Personal Deployment
**Actor**: Individual user deploying Khoj at home
**Flow**:
1. User starts Khoj with no auth configuration
2. Application runs immediately in single-user mode
3. User can search, chat, and configure without any login
4. No email setup or account creation required

**Success Criteria**: Zero-configuration personal deployment

### Scenario 2: Enterprise Deployment with AD
**Actor**: IT Administrator configuring Khoj for team use
**Flow**:
1. Admin starts Khoj with default anonymous mode
2. Admin navigates to Settings → Authentication → LDAP
3. Admin enters AD server details:
   - Server URL: `ldaps://ad.company.com:636`
   - Bind DN: `CN=khoj-service,OU=Service Accounts,DC=company,DC=com`
   - User Search Base: `OU=Users,DC=company,DC=com`
   - User Search Filter: `(sAMAccountName={username})`
   - Enable TLS: Yes
4. Admin clicks "Test Connection" - receives success message
5. Admin enables LDAP authentication
6. Team members can now log in with their AD credentials

**Success Criteria**: Seamless AD integration with UI-based configuration

### Scenario 3: LDAP User First Login
**Actor**: Employee accessing Khoj via LDAP
**Flow**:
1. User navigates to Khoj login page
2. User enters AD username and password
3. System validates against AD
4. User is logged in and can access all features
5. On subsequent visits, user data is preserved

**Success Criteria**: Transparent LDAP authentication with local data persistence

---

## Edge Cases and Failure Modes

### E-001: LDAP Server Unreachable
**Condition**: LDAP server is down or network is unreachable
**Behavior**: Display clear error "Cannot connect to authentication server. Please try again later or contact your administrator."
**Recovery**: Allow retry, do not expose LDAP internals to user

### E-002: Invalid LDAP Credentials
**Condition**: User enters wrong username/password
**Behavior**: Display generic "Invalid credentials" message (same as AD would)
**Security**: Do not reveal whether username exists

### E-003: LDAP User Locked/Disabled in AD
**Condition**: User account is disabled or locked in Active Directory
**Behavior**: Authentication fails with appropriate message
**Note**: Honor AD account state (locked, expired, disabled)

### E-004: LDAP Configuration Error
**Condition**: Admin saves invalid LDAP config (wrong bind DN, search base)
**Behavior**: Configuration UI shows validation errors before saving
**Safety**: Never save config that fails connection test

### E-005: Transition from Anonymous to LDAP
**Condition**: Admin enables LDAP on existing anonymous deployment with data
**Behavior**: Existing anonymous user data remains accessible
**Migration**: Provide option to associate anonymous data with LDAP user

### E-006: LDAP TLS Certificate Issues
**Condition**: AD server uses self-signed or untrusted certificate
**Behavior**: Configurable TLS verification (strict vs allow untrusted for testing)
**Security**: Log warning when verification is disabled

---

## Key Entities

1. **AuthMode** - Enum representing auth state: DISABLED, LDAP, GOOGLE_OAUTH, MAGIC_LINK
2. **LdapConfig** - Server configuration for LDAP connection
3. **KhojUser** - Extended with optional LDAP identity linkage
4. **LdapAuthBackend** - Authentication backend for LDAP validation

---

## Non-Functional Requirements

1. **Security**: LDAP bind passwords must be encrypted at rest
2. **Performance**: LDAP auth should complete within 2 seconds (typical AD latency)
3. **Reliability**: Connection pooling for LDAP connections
4. **Observability**: Log LDAP auth attempts (success/failure) for audit
5. **Compatibility**: Support both LDAP (port 389) and LDAPS (port 636)
6. **Standards**: Follow Python LDAP3 library best practices

---

## Dependencies to Add

- `ldap3` - Pure Python LDAP client library (preferred over python-ldap for portability)

---

## Notes

- The existing `--anonymous-mode` flag provides the foundation for "auth disabled by default"
- Only change required: flip default from `False` to `True`
- 79 `@requires(["authenticated"])` decorators already respect anonymous mode via `UserAuthenticationBackend`
- Windows AD uses `sAMAccountName` for usernames (not `uid` as in OpenLDAP)
