"use client";

import React, { useState } from 'react';
import styles from './loginPrompt.module.css';

interface LdapLoginFormProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

export default function LdapLoginForm({ onSuccess, onError }: LdapLoginFormProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/auth/ldap/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (response.status === 429) {
        setError('Too many login attempts. Please try again later.');
        onError?.('Too many login attempts. Please try again later.');
        return;
      }

      if (!response.ok) {
        setError('Invalid username or password.');
        onError?.('Invalid username or password.');
        return;
      }

      const data = await response.json();

      if (data.success) {
        onSuccess?.();
      } else {
        setError(data.message || 'Login failed.');
        onError?.(data.message || 'Login failed.');
      }
    } catch (err) {
      setError('Network error. Please check your connection and try again.');
      onError?.('Network error. Please check your connection and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <div className={styles.field}>
        <label htmlFor="ldap-username">
          Username
        </label>
        <input
          id="ldap-username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Enter your username"
          required
          disabled={isLoading}
          autoComplete="username"
          aria-describedby={error ? 'ldap-error' : undefined}
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="ldap-password">
          Password
        </label>
        <input
          id="ldap-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter your password"
          required
          disabled={isLoading}
          autoComplete="current-password"
          aria-describedby={error ? 'ldap-error' : undefined}
        />
      </div>

      {error && (
        <div 
          id="ldap-error" 
          className={styles.error} 
          role="alert"
          aria-live="polite"
        >
          {error}
        </div>
      )}

      <button
        type="submit"
        className={styles.submitButton}
        disabled={isLoading || !username || !password}
        aria-busy={isLoading}
      >
        {isLoading ? 'Signing in...' : 'Sign in with LDAP'}
      </button>
    </form>
  );
}
