/**
 * Maintainer Copilot Widget — Backend API client
 *
 * Typed client for public widget endpoints:
 * - GET  /public/widgets/{id}/config   → public config
 * - POST /public/widgets/{id}/session   → session token
 * - POST /public/widgets/{id}/chat/messages → submit message (body, not URL)
 * - GET  /public/widgets/{id}/chat/stream  → EventSource SSE (token + conversation_id only)
 *
 * Raw user message content is NEVER placed on the SSE URL.
 */

export interface WidgetConfig {
  widget_id: string;
  theme: string;
  greeting: string | null;
  position: string;
  enabled_tools: string[];
}

export interface SessionToken {
  token: string;
  expires_at: string;
  widget_id: string;
}

export interface MessageResponse {
  conversation_id: string;
}

/**
 * Fetch public widget config. Origin header is sent for validation.
 */
export async function fetchConfig(
  baseUrl: string,
  widgetId: string,
  origin: string,
): Promise<WidgetConfig> {
  const resp = await fetch(`${baseUrl}/public/widgets/${encodeURIComponent(widgetId)}/config`, {
    method: 'GET',
    headers: { Origin: origin },
  });

  if (!resp.ok) {
    throw new Error(`Config fetch failed: ${resp.status}`);
  }

  return resp.json() as Promise<WidgetConfig>;
}

/**
 * Request an anonymous session token. Origin header is sent for validation.
 */
export async function issueSession(
  baseUrl: string,
  widgetId: string,
  origin: string,
): Promise<SessionToken> {
  const resp = await fetch(`${baseUrl}/public/widgets/${encodeURIComponent(widgetId)}/session`, {
    method: 'POST',
    headers: { Origin: origin, 'Content-Type': 'application/json' },
  });

  if (!resp.ok) {
    throw new Error(`Session request failed: ${resp.status}`);
  }

  return resp.json() as Promise<SessionToken>;
}

/**
 * Submit a chat message via POST. Message content is in the request body,
 * never on the URL.
 */
export async function submitMessage(
  baseUrl: string,
  widgetId: string,
  sessionToken: string,
  message: string,
  conversationId?: string,
): Promise<MessageResponse> {
  const resp = await fetch(`${baseUrl}/public/widgets/${encodeURIComponent(widgetId)}/chat/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_token: sessionToken,
      conversation_id: conversationId,
    }),
  });

  if (!resp.ok) {
    throw new Error(`Message submit failed: ${resp.status}`);
  }

  return resp.json() as Promise<MessageResponse>;
}

/**
 * Create an EventSource URL for SSE streaming.
 *
 * Only token and conversation_id are on the URL — never raw message content.
 */
export function createEventSource(
  baseUrl: string,
  widgetId: string,
  sessionToken: string,
  conversationId: string,
): string {
  const params = new URLSearchParams({
    token: sessionToken,
    conversation_id: conversationId,
  });
  return `${baseUrl}/public/widgets/${encodeURIComponent(widgetId)}/chat/stream?${params.toString()}`;
}
