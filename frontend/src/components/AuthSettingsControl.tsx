'use client';

import { useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Key,
  User,
  Shield,
  Check,
  RotateCcw,
  X,
  Eye,
  EyeOff,
  AlertCircle,
} from 'lucide-react';
import {
  getApiToken,
  setApiToken,
  getActor,
  setActor,
  DEFAULT_DEV_TOKEN,
  DEFAULT_ACTOR,
} from '../lib/auth';

export function AuthSettingsControl() {
  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);
  const [tokenInput, setTokenInput] = useState('');
  const [actorInput, setActorInput] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Sync state when opening
  const loadCurrentSettings = useCallback(() => {
    setTokenInput(getApiToken());
    setActorInput(getActor());
  }, []);

  useEffect(() => {
    loadCurrentSettings();
  }, [loadCurrentSettings]);

  // Listen for external trigger to open settings (e.g. from 401 screen CTA)
  useEffect(() => {
    const handleOpen = () => {
      loadCurrentSettings();
      setIsOpen(true);
    };
    const handleAuthChanged = () => {
      loadCurrentSettings();
    };

    window.addEventListener('ecdat_open_auth_settings', handleOpen);
    window.addEventListener('ecdat_auth_changed', handleAuthChanged);
    return () => {
      window.removeEventListener('ecdat_open_auth_settings', handleOpen);
      window.removeEventListener('ecdat_auth_changed', handleAuthChanged);
    };
  }, [loadCurrentSettings]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setApiToken(tokenInput);
    setActor(actorInput);
    setSaveSuccess(true);
    // Invalidate queries so screens immediately retry with the new credentials
    queryClient.invalidateQueries();
    setTimeout(() => {
      setSaveSuccess(false);
      setIsOpen(false);
    }, 600);
  };

  const handleResetDefaults = () => {
    setTokenInput(DEFAULT_DEV_TOKEN);
    setActorInput(DEFAULT_ACTOR);
    setApiToken(DEFAULT_DEV_TOKEN);
    setActor(DEFAULT_ACTOR);
    queryClient.invalidateQueries();
    setSaveSuccess(true);
    setTimeout(() => {
      setSaveSuccess(false);
      setIsOpen(false);
    }, 600);
  };

  const isCustomToken = tokenInput !== DEFAULT_DEV_TOKEN && tokenInput.trim().length > 0;

  return (
    <>
      <button
        onClick={() => {
          loadCurrentSettings();
          setIsOpen(true);
        }}
        aria-label="API Authentication and Identity Settings"
        title={`API Token: ${tokenInput ? 'Configured' : 'Missing'} · Actor: ${actorInput}`}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-prominent)] transition-all"
      >
        <Key className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
        <span className="hidden sm:inline">Auth</span>
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            isCustomToken
              ? 'bg-[var(--crypto-pqc)] ring-2 ring-[var(--crypto-pqc-bg)]'
              : 'bg-[var(--crypto-grover)]'
          }`}
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="auth-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        >
          <div
            className="bg-[var(--surface-card)] border border-[var(--border-prominent)] rounded-xl w-full max-w-md shadow-2xl p-6 space-y-5 font-mono text-xs text-[var(--text-primary)]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between border-b border-[var(--border-subtle)] pb-3">
              <div className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)]">
                <Shield className="w-4 h-4 text-[var(--crypto-pqc)]" />
                <span id="auth-modal-title">API Authentication & Actor Identity</span>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                aria-label="Close settings dialog"
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1 rounded transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Explanatory callout */}
            <div className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[11px] text-[var(--text-secondary)] leading-relaxed space-y-1">
              <div className="flex items-center gap-1.5 font-bold text-[var(--text-primary)]">
                <AlertCircle className="w-3.5 h-3.5 text-[var(--crypto-pqc)] flex-shrink-0" />
                <span>Production Security Requirement</span>
              </div>
              <p>
                All API routes (except <code className="text-[var(--crypto-pqc)]">/health</code>) require{' '}
                <code className="text-[var(--crypto-pqc)]">Authorization: Bearer &lt;token&gt;</code>. All state writes
                require <code className="text-[var(--crypto-pqc)]">X-ECDAT-Actor: &lt;identity&gt;</code> for the audit log.
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSave} className="space-y-4">
              {/* Token Input */}
              <div className="space-y-1">
                <label htmlFor="auth-token-input" className="block font-bold text-[var(--text-secondary)]">
                  API Bearer Token
                </label>
                <div className="relative flex items-center">
                  <input
                    id="auth-token-input"
                    type={showToken ? 'text' : 'password'}
                    value={tokenInput}
                    onChange={(e) => setTokenInput(e.target.value)}
                    placeholder="Enter ECDAT_API_TOKEN"
                    className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-3 py-2 pr-9 text-xs font-mono text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)] focus:ring-1 focus:ring-[var(--crypto-pqc)]"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken(!showToken)}
                    aria-label={showToken ? 'Hide API token' : 'Show API token'}
                    className="absolute right-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1"
                  >
                    {showToken ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <span className="text-[10px] text-[var(--text-muted)] block">
                  Defaults to <code className="text-[var(--text-secondary)]">NEXT_PUBLIC_ECDAT_API_TOKEN</code> or local dev token.
                </span>
              </div>

              {/* Actor Identity Input */}
              <div className="space-y-1">
                <label htmlFor="auth-actor-input" className="block font-bold text-[var(--text-secondary)]">
                  Operator Identity (X-ECDAT-Actor)
                </label>
                <div className="relative flex items-center">
                  <User className="absolute left-2.5 w-3.5 h-3.5 text-[var(--text-muted)]" />
                  <input
                    id="auth-actor-input"
                    type="text"
                    value={actorInput}
                    onChange={(e) => setActorInput(e.target.value)}
                    placeholder="frontend-operator"
                    className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded pl-8 pr-3 py-2 text-xs font-mono text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)] focus:ring-1 focus:ring-[var(--crypto-pqc)]"
                  />
                </div>
                <span className="text-[10px] text-[var(--text-muted)] block">
                  Identifies the operator in cryptographic attestation and audit logs.
                </span>
              </div>

              {/* Buttons */}
              <div className="pt-2 flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={handleResetDefaults}
                  className="px-3 py-1.5 rounded border border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all inline-flex items-center gap-1.5 text-xs"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Reset Defaults</span>
                </button>

                <button
                  type="submit"
                  className="px-4 py-1.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold hover:opacity-90 transition-all inline-flex items-center gap-1.5 text-xs"
                >
                  {saveSuccess ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>Saved & Applied</span>
                    </>
                  ) : (
                    <span>Save & Apply</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
