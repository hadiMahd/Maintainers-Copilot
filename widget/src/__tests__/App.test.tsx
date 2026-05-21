import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import React from 'react'

import App from '../App'

const mockConfig = {
  widget_id: 'wid-1',
  theme: 'dark',
  greeting: 'Hello!',
  position: 'bottom-right',
  enabled_tools: ['classify_issue'],
}

beforeEach(() => {
  ;(window as unknown as Record<string, unknown>).__WIDGET_ID__ = 'wid-1'
  ;(window as unknown as Record<string, unknown>).__ORIGIN__ = 'https://example.com'
})

afterEach(() => {
  delete (window as unknown as Record<string, unknown>).__WIDGET_ID__
  delete (window as unknown as Record<string, unknown>).__ORIGIN__
  cleanup()
})

describe('App', () => {
  it('renders collapsed bubble on load', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockConfig,
    } as Response)

    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /open chat/i })).toBeTruthy()
    })
  })

  it('renders expanded panel when bubble is clicked', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockConfig,
    } as Response)

    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('button')).toBeTruthy()
    })

    const bubble = screen.getByRole('button')
    bubble.click()

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/type a message/i)).toBeTruthy()
    })
  })

  it('applies dark theme class', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockConfig,
    } as Response)

    const { container } = render(<App />)

    await waitFor(() => {
      const widget = container.querySelector('.mc-widget')
      expect(widget?.classList.contains('mc-widget--dark')).toBe(true)
    })
  })

  it('shows error state when config fetch fails', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: false,
      status: 403,
    } as Response)

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText(/widget unavailable/i)).toBeTruthy()
    })
  })

  it('shows blocked state when origin is not allowed', async () => {
    vi.spyOn(window, 'fetch').mockResolvedValue({
      ok: false,
      status: 403,
    } as Response)

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText(/widget unavailable/i)).toBeTruthy()
    })
  })
})
