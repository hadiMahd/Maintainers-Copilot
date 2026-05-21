import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchConfig, issueSession, submitMessage, createEventSource } from '../api'

beforeEach(() => {
  vi.resetAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('fetchConfig', () => {
  it('fetches public config with Origin header', async () => {
    const mockConfig = {
      widget_id: 'wid-1',
      theme: 'dark',
      greeting: 'Hello!',
      position: 'bottom-right',
      enabled_tools: [],
    }

    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockConfig,
      headers: { get: () => 'req-1' },
    } as unknown as Response)

    const config = await fetchConfig('https://api.example.com', 'wid-1', 'https://example.com')

    expect(config.widget_id).toBe('wid-1')
    expect(config.greeting).toBe('Hello!')
    expect(config.position).toBe('bottom-right')

    const fetchCall = (window.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(fetchCall[0]).toContain('/public/widgets/wid-1/config')
    expect(fetchCall[0]).not.toContain('message=')
  })

  it('throws on 403 response', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: false,
      status: 403,
    } as unknown as Response)

    await expect(fetchConfig('https://api.example.com', 'wid-1', 'https://evil.com')).rejects.toThrow()
  })
})

describe('issueSession', () => {
  it('posts to session endpoint with Origin header', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ token: 'abc123', expires_at: '2026-01-01T00:00:00Z', widget_id: 'wid-1' }),
    } as unknown as Response)

    const result = await issueSession('https://api.example.com', 'wid-1', 'https://example.com')

    expect(result.token).toBe('abc123')
    expect(result.widget_id).toBe('wid-1')

    const fetchCall = (window.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(fetchCall[0]).toContain('/public/widgets/wid-1/session')
    expect(fetchCall[1]?.method).toBe('POST')
  })
})

describe('submitMessage', () => {
  it('posts message to messages endpoint without message in URL', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ conversation_id: 'conv-1' }),
    } as unknown as Response)

    const result = await submitMessage(
      'https://api.example.com',
      'wid-1',
      'abc123',
      'Hello world',
    )

    expect(result.conversation_id).toBe('conv-1')

    const fetchCall = (window.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    const url = fetchCall[0] as string
    expect(url).not.toContain('Hello')
    expect(url).not.toContain('world')
    expect(url).not.toContain('message=')

    const body = JSON.parse(fetchCall[1]?.body as string)
    expect(body.message).toBe('Hello world')
    expect(body.session_token).toBe('abc123')
  })
})

describe('createEventSource', () => {
  it('creates EventSource URL without raw message content', () => {
    const url = createEventSource(
      'https://api.example.com',
      'wid-1',
      'abc123',
      'conv-1',
    )

    expect(url).toContain('/public/widgets/wid-1/chat/stream')
    expect(url).toContain('token=abc123')
    expect(url).toContain('conversation_id=conv-1')
    expect(url).not.toContain('message=')
    expect(url).not.toContain('Hello')
  })
})
