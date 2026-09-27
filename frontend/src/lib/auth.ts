/**
 * Authentication and Operator Identity utilities for ECDAT Frontend.
 *
 * Requirements (M1):
 * - Attach `Authorization: Bearer <token>` to all API requests (except /health).
 * - Attach `X-ECDAT-Actor: <actor>` to all state-changing API writes and requests.
 * - Support `NEXT_PUBLIC_ECDAT_API_TOKEN` fallback or locally persisted settings override.
 * - Support `NEXT_PUBLIC_ECDAT_ACTOR` fallback or locally persisted actor override (defaults to 'frontend-operator').
 */

export const STORAGE_KEY_TOKEN = 'ecdat_api_token';
export const STORAGE_KEY_ACTOR = 'ecdat_actor';
export const DEFAULT_DEV_TOKEN = 'ecdat-dev-insecure-token';
export const DEFAULT_ACTOR = 'frontend-operator';

export class ApiError extends Error {
  status: number;
  body?: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export function isUnauthorizedError(error: unknown): boolean {
  if (!error) return false;
  if (error instanceof ApiError && error.status === 401) return true;
  if (typeof error === 'object' && error !== null && 'status' in error && (error as any).status === 401) {
    return true;
  }
  if (
    error instanceof Error &&
    (error.message.includes('401') ||
      error.message.toLowerCase().includes('unauthorized') ||
      error.message.toLowerCase().includes('not authenticated'))
  ) {
    return true;
  }
  return false;
}

export function getApiToken(): string {
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_TOKEN);
      if (stored && stored.trim()) {
        return stored.trim();
      }
    } catch {
      // Ignore localStorage read errors in sandboxed contexts
    }
  }
  return process.env.NEXT_PUBLIC_ECDAT_API_TOKEN || DEFAULT_DEV_TOKEN;
}

export function setApiToken(token: string): void {
  if (typeof window !== 'undefined') {
    try {
      if (!token || !token.trim()) {
        localStorage.removeItem(STORAGE_KEY_TOKEN);
      } else {
        localStorage.setItem(STORAGE_KEY_TOKEN, token.trim());
      }
      window.dispatchEvent(new CustomEvent('ecdat_auth_changed', { detail: { token } }));
    } catch {
      // Ignore localStorage write errors
    }
  }
}

export function getActor(): string {
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_ACTOR);
      if (stored && stored.trim()) {
        return stored.trim();
      }
    } catch {
      // Ignore localStorage read errors
    }
  }
  return process.env.NEXT_PUBLIC_ECDAT_ACTOR || DEFAULT_ACTOR;
}

export function setActor(actor: string): void {
  if (typeof window !== 'undefined') {
    try {
      if (!actor || !actor.trim()) {
        localStorage.removeItem(STORAGE_KEY_ACTOR);
      } else {
        localStorage.setItem(STORAGE_KEY_ACTOR, actor.trim());
      }
      window.dispatchEvent(new CustomEvent('ecdat_auth_changed', { detail: { actor } }));
    } catch {
      // Ignore localStorage write errors
    }
  }
}

export function getAuthHeaders(): Record<string, string> {
  const token = getApiToken();
  const actor = getActor();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (actor) {
    headers['X-ECDAT-Actor'] = actor;
  }

  return headers;
}

export function triggerOpenAuthSettings(): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('ecdat_open_auth_settings'));
  }
}
