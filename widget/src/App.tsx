import React, { useCallback, useEffect, useRef, useState } from 'react';
import { fetchConfig, issueSession, submitMessage, createEventSource, WidgetConfig } from './api';
import { postResize, RESIZE_EVENT_TYPE } from './messages';
import './styles.css';

type Theme = 'light' | 'dark';
type Position = 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}

function getWidgetId(): string | undefined {
  return (typeof window !== 'undefined' ? (window as Record<string, unknown>).__WIDGET_ID__ : undefined) as string | undefined;
}

function getOrigin(): string | undefined {
  return (typeof window !== 'undefined' ? (window as Record<string, unknown>).__ORIGIN__ : undefined) as string | undefined;
}

function resolveBaseUrl(): string {
  if (typeof window === 'undefined') return '';
  const loc = window.location;
  return `${loc.protocol}//${loc.host}`;
}

function App(): React.ReactElement {
  const [config, setConfig] = useState<WidgetConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [sessionToken, setSessionToken] = useState<string>('');
  const [conversationId, setConversationId] = useState<string>('');
  const [streamInterrupted, setStreamInterrupted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  const baseUrl = resolveBaseUrl();

  useEffect(() => {
    const widgetId = getWidgetId();
    if (!widgetId) {
      setError('Widget ID is not configured');
      return;
    }

    const origin = getOrigin() || window.location.origin;
    const loadConfig = async () => {
      try {
        const cfg = await fetchConfig(baseUrl, widgetId, origin);
        setConfig(cfg);

        const session = await issueSession(baseUrl, widgetId, origin);
        setSessionToken(session.token);
      } catch {
        setError('Widget unavailable');
      }
    };

    loadConfig();
  }, [baseUrl]);

  useEffect(() => {
    if (expanded && config) {
      postResize(window.parent, 500, 380);
    }
  }, [expanded, config]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(async () => {
    const widgetId = getWidgetId();
    if (!input.trim() || !sessionToken || sending || !widgetId) return;

    const userMsg: ChatMessage = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setSending(true);
    setStreamInterrupted(false);

    try {
      const resp = await submitMessage(baseUrl, widgetId, sessionToken, userMsg.content, conversationId || undefined);
      setConversationId(resp.conversation_id);

      if (esRef.current) {
        esRef.current.close();
      }

      const url = createEventSource(baseUrl, widgetId, sessionToken, resp.conversation_id);
      const es = new EventSource(url);
      esRef.current = es;

      let assistantContent = '';
      const assistantMsgId = Date.now().toString();
      setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }]);

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event_type === 'message_delta' && data.content) {
            assistantContent += data.content;
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === 'assistant' && last.streaming) {
                last.content = assistantContent;
              }
              return updated;
            });
          }
          if (data.event_type === 'done' || data.event_type === 'error') {
            es.close();
            esRef.current = null;
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === 'assistant') {
                last.streaming = false;
              }
              return updated;
            });
            setSending(false);
          }
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        setMessages(prev => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === 'assistant') {
            last.streaming = false;
          }
          return updated;
        });
        setSending(false);
        setStreamInterrupted(true);
      };
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Failed to send message.', streaming: false }]);
      setSending(false);
    }
  }, [input, sessionToken, sending, baseUrl, conversationId]);

  const handleRetry = useCallback(() => {
    setStreamInterrupted(false);
    setInput('');
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (error) {
    return (
      <div className={`mc-widget mc-widget--light mc-error`}>
        <div className="mc-error__icon">⚠</div>
        <div>{error}</div>
      </div>
    );
  }

  if (!config) {
    return <div className="mc-widget mc-widget--light" style={{ width: 56, height: 56 }} />;
  }

  const themeClass = config.theme === 'dark' ? 'mc-widget--dark' : 'mc-widget--light';
  const positionClass = `mc-widget--${config.position || 'bottom-right'}`;

  return (
    <div className={`mc-widget ${themeClass} ${positionClass}`}>
      {!expanded ? (
        <button
          className="mc-bubble"
          onClick={() => setExpanded(true)}
          aria-label="Open chat"
        >
          <svg className="mc-bubble__icon" viewBox="0 0 24 24">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z" />
          </svg>
        </button>
      ) : (
        <div className="mc-panel">
          <div className="mc-panel__header">
            <span>{config.greeting || 'Chat'}</span>
            <button className="mc-panel__close" onClick={() => setExpanded(false)} aria-label="Close">
              ✕
            </button>
          </div>
          <div className="mc-messages">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`mc-message mc-message--${msg.role}${msg.streaming ? ' mc-message--streaming' : ''}`}
              >
                {msg.content}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          {streamInterrupted && (
            <div style={{ padding: '8px 16px', textAlign: 'center' }}>
              <button onClick={handleRetry} style={{ fontSize: 12, cursor: 'pointer' }}>
                Stream interrupted — retry
              </button>
            </div>
          )}
          <div className="mc-input-bar">
            <input
              className="mc-input"
              placeholder="Type a message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending}
            />
            <button className="mc-send" onClick={handleSend} disabled={sending || !input.trim()}>
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
