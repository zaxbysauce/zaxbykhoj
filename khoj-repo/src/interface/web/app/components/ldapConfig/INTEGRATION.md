// src/interface/web/app/components/ldapConfig/INTEGRATION.md
// Integration guide for adding LDAP configuration to Khoj settings page

## LDAP Configuration Component Integration Guide

### Overview

This guide explains how to integrate the LDAP Configuration section into the Khoj settings page.

### Files Created

1. **`ldapConfig.tsx`** - Main component with form, validation, and API integration
2. **`ldapConfig.module.css`** - Component-specific styles
3. **`index.ts`** - Module exports

### Integration Steps

#### 1. Import the Component

Add the following import to `src/interface/web/app/settings/page.tsx`:

```typescript
import { LdapConfigSection } from "../components/ldapConfig";
```

#### 2. Add Admin Check to UserConfig Interface

Extend the `UserConfig` interface in `src/interface/web/app/common/auth.ts`:

```typescript
export interface UserConfig {
    // ... existing fields
    is_admin: boolean;  // Add this field
}
```

#### 3. Add LDAP Section to Settings Page

Add the LDAP configuration card to the settings page. Insert this within the settings grid:

```tsx
{/* Add after the API Keys section or in a new "Authentication" section */}
<div className="section grid gap-8">
    <div className="text-2xl">Authentication</div>
    <div className="cards flex flex-wrap gap-16">
        <LdapConfigSection 
            isAdmin={userConfig?.is_admin ?? false}
            onSave={async (config) => {
                // Optional: Add any post-save logic
                console.log("LDAP config saved:", config);
            }}
        />
    </div>
</div>
```

#### 4. Required API Endpoints

The following backend API endpoints need to be implemented:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config/ldap` | GET | Fetch current LDAP configuration |
| `/api/config/ldap` | POST | Save LDAP configuration |
| `/api/config/ldap/test` | POST | Test LDAP connection |

#### 5. Response Formats

**GET /api/config/ldap Response:**
```json
{
    "server_url": "ldaps://ad.company.com:636",
    "bind_dn": "CN=service,OU=Accounts,DC=company,DC=com",
    "bind_password": "***encrypted***",
    "user_search_base": "OU=Users,DC=company,DC=com",
    "user_search_filter": "(sAMAccountName={username})",
    "use_tls": true,
    "verify_tls_certificate": true,
    "enabled": false
}
```

**POST /api/config/ldap/test Response (Success):**
```json
{
    "success": true,
    "message": "Successfully connected to LDAP server",
    "details": {
        "bind_success": true,
        "search_success": true,
        "users_found": 150
    }
}
```

**POST /api/config/ldap/test Response (Error):**
```json
{
    "success": false,
    "message": "Failed to bind to LDAP server: Invalid credentials"
}
```

### Component Architecture

```
LdapConfigSection (Main Container)
├── Form Provider (react-hook-form + zod)
├── Enable LDAP Toggle
├── Server Configuration Section
│   ├── Server URL Input
│   ├── Use TLS Toggle
│   └── Verify TLS Certificate Toggle (conditional)
├── Bind Credentials Section
│   ├── Bind DN Input
│   └── Bind Password Input (with visibility toggle)
├── User Search Section
│   ├── User Search Base Input
│   └── User Search Filter Input
├── Test Connection Button
├── Connection Status Alert
└── Action Buttons (Save/Cancel)
```

### State Management

The component uses a hybrid approach:

1. **Form State**: Managed by `react-hook-form` with `zod` validation
2. **Connection Test State**: Local component state for test status and results
3. **Server State**: SWR for fetching/synchronizing with backend

### Validation Rules

| Field | Rules |
|-------|-------|
| Server URL | Required, must start with `ldap://` or `ldaps://` |
| Bind DN | Required, must contain LDAP attributes (CN=, DC=, OU=) |
| Bind Password | Required, minimum 8 characters |
| User Search Base | Required, must contain LDAP attributes |
| User Search Filter | Required, must contain `{username}` placeholder |

### Accessibility Features

- Semantic HTML with proper heading hierarchy
- ARIA labels on all interactive elements
- Password visibility toggle with `aria-pressed` state
- Alert messages with `role="alert"` and `aria-live` regions
- Keyboard navigation support for all controls
- Focus indicators on all interactive elements
- High contrast mode support
- Reduced motion support

### Styling Guidelines

The component uses Tailwind CSS classes following Khoj's design system:

- **Cards**: `border border-gray-300 shadow-md rounded-lg`
- **Inputs**: Standard shadcn/ui Input component
- **Buttons**: Primary (Save), Secondary (Test), Outline (Cancel)
- **Spacing**: Consistent with existing settings cards (`w-full lg:w-5/12`)

### Security Considerations

1. **Password Handling**: 
   - Password is masked by default
   - Toggle for visibility with keyboard support
   - Password should be encrypted at rest on backend

2. **Admin Access**:
   - Component checks `isAdmin` prop
   - Shows restricted message for non-admin users
   - "Admin Only" badge for visibility

3. **TLS Configuration**:
   - TLS enabled by default
   - Certificate verification enabled by default
   - Warning when TLS is disabled

### Error Handling

The component handles the following error scenarios:

1. **Validation Errors**: Inline form errors using zod schema
2. **Fetch Errors**: Alert component when config fails to load
3. **Connection Test Errors**: Detailed error messages from backend
4. **Save Errors**: Toast notifications with error details

### Testing Checklist

Before deploying, verify:

- [ ] Form validation works for all fields
- [ ] Password show/hide toggle functions correctly
- [ ] TLS toggle disables certificate verification toggle
- [ ] Connection test displays appropriate loading/success/error states
- [ ] Save button is disabled until connection test passes
- [ ] Cancel button resets form to saved values
- [ ] Non-admin users see access denied message
- [ ] Keyboard navigation works for all controls
- [ ] Screen reader announces form errors and alerts
- [ ] Mobile responsive layout works correctly

### Future Enhancements

Potential improvements for future iterations:

1. **LDAP Group Mapping**: Map LDAP groups to Khoj roles
2. **Multiple LDAP Servers**: Support for LDAP server failover
3. **User Attribute Mapping**: Map custom LDAP attributes to Khoj user fields
4. **Test User Search**: Search for a specific user to verify configuration
5. **Import Users**: Bulk import users from LDAP

### Dependencies

Ensure these dependencies are installed:

```bash
npm install react-hook-form zod @hookform/resolvers swr
```

All UI components use existing shadcn/ui components from the project.

### Troubleshooting

**Issue: Form doesn't populate with existing config**
- Verify `/api/config/ldap` endpoint returns data
- Check browser console for fetch errors
- Ensure SWR configuration is correct

**Issue: Connection test fails**
- Verify LDAP server is accessible from Khoj server
- Check firewall rules for LDAP ports (389/636)
- Validate bind DN and password

**Issue: Save button disabled**
- Connection test must pass before saving
- Check connection test status indicator
- Verify all required fields are filled
