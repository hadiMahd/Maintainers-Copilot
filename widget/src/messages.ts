/**
 * Maintainer Copilot Widget — postMessage resize channel
 *
 * The widget iframe sends resize messages to the parent window.
 * Only messages with the expected event type and valid dimensions are accepted.
 */

export const RESIZE_EVENT_TYPE = 'maintainer-copilot-widget:resize';

export interface ResizeMessage {
  type: typeof RESIZE_EVENT_TYPE;
  height: number;
  width: number;
}

const DEFAULT_HEIGHT = 500;
const DEFAULT_WIDTH = 380;
const MAX_HEIGHT = 800;
const MAX_WIDTH = 600;
const MIN_HEIGHT = 200;
const MIN_WIDTH = 280;

/**
 * Send a resize message to the parent window.
 */
export function postResize(
  targetWindow: Window,
  height?: number,
  width?: number,
  targetOrigin: string = '*',
): void {
  const msg: ResizeMessage = {
    type: RESIZE_EVENT_TYPE,
    height: clamp(height ?? DEFAULT_HEIGHT, MIN_HEIGHT, MAX_HEIGHT),
    width: clamp(width ?? DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH),
  };
  targetWindow.postMessage(msg, targetOrigin);
}

/**
 * Set up a listener for resize messages from the widget iframe.
 * Returns a cleanup function.
 */
export function setupResizeListener(
  handler: (dimensions: { height: number; width: number }) => void,
): () => void {
  const listener = (event: MessageEvent) => {
    const data = event.data;
    if (!data || typeof data !== 'object') return;
    if (data.type !== RESIZE_EVENT_TYPE) return;

    const height = data.height;
    const width = data.width;

    if (typeof height !== 'number' || typeof width !== 'number') return;
    if (height < MIN_HEIGHT || height > MAX_HEIGHT) return;
    if (width < MIN_WIDTH || width > MAX_WIDTH) return;

    handler({ height, width });
  };

  window.addEventListener('message', listener);
  return () => window.removeEventListener('message', listener);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
