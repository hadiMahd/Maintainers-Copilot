import { describe, expect, it, vi } from 'vitest'

import { postResize, setupResizeListener } from '../messages'

describe('postResize', () => {
  it('sends resize message to parent with correct type', () => {
    const postMessage = vi.fn()
    const mockParent = { postMessage } as unknown as Window

    postResize(mockParent, 500, 380, '*')

    expect(postMessage).toHaveBeenCalledTimes(1)
    expect(postMessage).toHaveBeenCalledWith(
      { type: 'maintainer-copilot-widget:resize', height: 500, width: 380 },
      '*',
    )
  })

  it('uses default dimensions when not provided', () => {
    const postMessage = vi.fn()
    const mockParent = { postMessage } as unknown as Window

    postResize(mockParent, undefined, undefined, '*')

    expect(postMessage).toHaveBeenCalledWith(
      { type: 'maintainer-copilot-widget:resize', height: 500, width: 380 },
      '*',
    )
  })
})

describe('setupResizeListener', () => {
  it('calls handler on valid resize message', () => {
    const handler = vi.fn()
    const cleanup = setupResizeListener(handler)

    const event = new MessageEvent('message', {
      data: { type: 'maintainer-copilot-widget:resize', height: 600, width: 400 },
      origin: 'https://example.com',
    })
    window.dispatchEvent(event)

    expect(handler).toHaveBeenCalledWith({ height: 600, width: 400 })

    cleanup()
  })

  it('ignores non-resize messages', () => {
    const handler = vi.fn()
    const cleanup = setupResizeListener(handler)

    const event = new MessageEvent('message', {
      data: { type: 'some-other-event' },
      origin: 'https://example.com',
    })
    window.dispatchEvent(event)

    expect(handler).not.toHaveBeenCalled()

    cleanup()
  })

  it('ignores messages with invalid dimensions', () => {
    const handler = vi.fn()
    const cleanup = setupResizeListener(handler)

    const event = new MessageEvent('message', {
      data: { type: 'maintainer-copilot-widget:resize', height: -100, width: 400 },
      origin: 'https://example.com',
    })
    window.dispatchEvent(event)

    expect(handler).not.toHaveBeenCalled()

    cleanup()
  })

  it('ignores messages exceeding max dimensions', () => {
    const handler = vi.fn()
    const cleanup = setupResizeListener(handler)

    const event = new MessageEvent('message', {
      data: { type: 'maintainer-copilot-widget:resize', height: 99999, width: 400 },
      origin: 'https://example.com',
    })
    window.dispatchEvent(event)

    expect(handler).not.toHaveBeenCalled()

    cleanup()
  })
})
