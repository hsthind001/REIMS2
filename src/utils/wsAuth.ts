/**
 * WebSocket auth URL builder (E1-S2).
 * Builds WS URL with token and org_id query params for authenticated connections.
 */
import { useAuthStore } from '../store/authStore';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/api\/v1\/?$/, '').replace(/\/$/, '') + '/api/v1';

/** Returns WebSocket URL with auth params, or null if token/org missing. */
export function buildWsUrl(path: string): string | null {
  const token = localStorage.getItem('auth_token');
  const { currentOrganization } = useAuthStore.getState();
  if (!token || !currentOrganization?.id) return null;
  const base = new URL(API_BASE);
  const protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
  const params = new URLSearchParams({ token, org_id: String(currentOrganization.id) });
  return `${protocol}//${base.host}${path}?${params}`;
}
