"use client";

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import styles from './ldapConfig.module.css';

// Form validation schema
const ldapConfigSchema = z.object({
  server_url: z.string().min(1, "Server URL is required").refine(
    (val) => val.startsWith('ldap://') || val.startsWith('ldaps://'),
    "URL must start with ldap:// or ldaps://"
  ),
  user_search_base: z.string().min(1, "Search base is required"),
  user_search_filter: z.string().min(1, "Search filter is required"),
  use_tls: z.boolean().default(true),
  tls_verify: z.boolean().default(true),
  tls_ca_bundle_path: z.string().optional(),
  enabled: z.boolean().default(false),
});

type LdapConfigForm = z.infer<typeof ldapConfigSchema>;

interface LdapConfigProps {
  isAdmin: boolean;
}

export default function LdapConfig({ isAdmin }: LdapConfigProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [saveResult, setSaveResult] = useState<{ success: boolean; message: string } | null>(null);
  const [initialData, setInitialData] = useState<LdapConfigForm | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isDirty },
    reset,
  } = useForm<LdapConfigForm>({
    resolver: zodResolver(ldapConfigSchema),
    defaultValues: {
      server_url: 'ldaps://ad.company.com:636',
      user_search_base: 'OU=Users,DC=company,DC=com',
      user_search_filter: '(sAMAccountName={username})',
      use_tls: true,
      tls_verify: true,
      tls_ca_bundle_path: '',
      enabled: false,
    },
  });

  const useTls = watch('use_tls');

  // Fetch current config on mount
  useEffect(() => {
    if (isAdmin) {
      fetchConfig();
    }
  }, [isAdmin]);

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/settings/ldap');
      if (response.ok) {
        const data = await response.json();
        setInitialData(data);
        reset(data);
      }
    } catch (error) {
      console.error('Failed to fetch LDAP config:', error);
    }
  };

  const testConnection = async (data: LdapConfigForm) => {
    setIsTesting(true);
    setTestResult(null);

    try {
      const response = await fetch('/api/settings/ldap/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Connection test failed. Please check your settings.',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const onSubmit = async (data: LdapConfigForm) => {
    setIsLoading(true);
    setSaveResult(null);

    try {
      const response = await fetch('/api/settings/ldap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        setSaveResult({
          success: true,
          message: 'LDAP configuration saved successfully.',
        });
        // Refresh config to get server-side state
        fetchConfig();
      } else {
        const error = await response.json();
        setSaveResult({
          success: false,
          message: error.detail || 'Failed to save configuration.',
        });
      }
    } catch (error) {
      setSaveResult({
        success: false,
        message: 'Network error. Please try again.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAdmin) {
    return (
      <div className={styles.container}>
        <p className={styles.error}>
          Admin access required to configure LDAP authentication.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>LDAP Authentication</h2>
        <span className={styles.badge}>Admin Only</span>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
        <div className={styles.section}>
          <h3>Server Configuration</h3>
          
          <div className={styles.field}>
            <label htmlFor="server_url">
              Server URL
              <span className={styles.required}>*</span>
            </label>
            <input
              id="server_url"
              type="text"
              {...register('server_url')}
              placeholder="ldaps://ad.company.com:636"
              aria-invalid={errors.server_url ? 'true' : 'false'}
              aria-describedby={errors.server_url ? 'server_url-error' : undefined}
            />
            {errors.server_url && (
              <span id="server_url-error" className={styles.error} role="alert">
                {errors.server_url.message}
              </span>
            )}
            <p className={styles.help}>
              LDAP server URL. Use ldaps:// for LDAPS (port 636) or ldap:// for StartTLS (port 389).
            </p>
          </div>

          <div className={styles.field}>
            <label htmlFor="user_search_base">
              User Search Base
              <span className={styles.required}>*</span>
            </label>
            <input
              id="user_search_base"
              type="text"
              {...register('user_search_base')}
              placeholder="OU=Users,DC=company,DC=com"
              aria-invalid={errors.user_search_base ? 'true' : 'false'}
            />
            {errors.user_search_base && (
              <span className={styles.error} role="alert">{errors.user_search_base.message}</span>
            )}
            <p className={styles.help}>
              Base DN for user searches (e.g., OU=Users,DC=company,DC=com for Active Directory).
            </p>
          </div>

          <div className={styles.field}>
            <label htmlFor="user_search_filter">
              User Search Filter
              <span className={styles.required}>*</span>
            </label>
            <input
              id="user_search_filter"
              type="text"
              {...register('user_search_filter')}
              placeholder="(sAMAccountName={username})"
              aria-invalid={errors.user_search_filter ? 'true' : 'false'}
            />
            {errors.user_search_filter && (
              <span className={styles.error} role="alert">{errors.user_search_filter.message}</span>
            )}
            <p className={styles.help}>
              LDAP filter to find users. Use {'{username}'} as placeholder.
            </p>
          </div>
        </div>

        <div className={styles.section}>
          <h3>TLS Settings</h3>
          
          <div className={styles.field}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                {...register('use_tls')}
              />
              Enable TLS
            </label>
            <p className={styles.help}>
              Enable TLS encryption for LDAP connections.
            </p>
          </div>

          {useTls && (
            <>
              <div className={styles.field}>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    {...register('tls_verify')}
                  />
                  Verify TLS Certificate
                </label>
                <p className={styles.help}>
                  Verify the server&apos;s TLS certificate. Disable only for testing with self-signed certificates.
                </p>
              </div>

              <div className={styles.field}>
                <label htmlFor="tls_ca_bundle_path">
                  CA Bundle Path (Optional)
                </label>
                <input
                  id="tls_ca_bundle_path"
                  type="text"
                  {...register('tls_ca_bundle_path')}
                  placeholder="/etc/ssl/certs/ca-certificates.crt"
                />
                <p className={styles.help}>
                  Path to custom CA bundle for certificate verification.
                </p>
              </div>
            </>
          )}
        </div>

        <div className={styles.section}>
          <h3>Enable Authentication</h3>
          
          <div className={styles.field}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                {...register('enabled')}
              />
              Enable LDAP Authentication
            </label>
            <p className={styles.help}>
              Enable LDAP authentication for user logins. Ensure settings are correct before enabling.
            </p>
          </div>
        </div>

        {testResult && (
          <div className={`${styles.alert} ${testResult.success ? styles.success : styles.error}`}>
            {testResult.message}
          </div>
        )}

        {saveResult && (
          <div className={`${styles.alert} ${saveResult.success ? styles.success : styles.error}`}>
            {saveResult.message}
          </div>
        )}

        <div className={styles.actions}>
          <button
            type="button"
            onClick={handleSubmit(testConnection)}
            disabled={isTesting || isLoading}
            className={styles.testButton}
          >
            {isTesting ? 'Testing...' : 'Test Connection'}
          </button>
          
          <button
            type="submit"
            disabled={isLoading || !isDirty}
            className={styles.saveButton}
          >
            {isLoading ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </form>
    </div>
  );
}
