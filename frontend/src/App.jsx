import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  ArrowUp,
  Building2,
  FileText,
  Headphones,
  Laptop,
  PackageCheck,
  Store,
  UserRound,
  UserRoundCog,
} from 'lucide-react'
import csubLogoHeader from './assets/csub-logo-header.png'

const DEFAULT_API_BASE_URL =
  'https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod'
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/+$/, '')
const CHAT_API_URL = import.meta.env.VITE_API_URL || `${API_BASE_URL}/v1/chat`
const HEALTH_API_URL =
  import.meta.env.VITE_HEALTH_URL || `${API_BASE_URL}/v1/health`
const CHAT_TIMEOUT_MS = 32_000
const HEALTH_TIMEOUT_MS = 8_000

const roles = [
  { id: 'requester', label: 'Faculty or staff', Icon: UserRound },
  { id: 'vendor', label: 'Vendor or supplier', Icon: Store },
  { id: 'internal_staff', label: 'Support staff', Icon: Headphones },
]

const starters = [
  {
    text: 'How do I buy software or a subscription?',
    Icon: Laptop,
  },
  {
    text: 'I need help with a new supplier.',
    Icon: Store,
  },
  {
    text: 'How do I create a receipt in CSUBUY?',
    Icon: PackageCheck,
  },
  {
    text: 'How do I update my CSUBUY profile?',
    Icon: UserRoundCog,
  },
]

function sourceName(path = 'CSUB procurement source') {
  return path.split('/').pop() || path
}

async function fetchJson(url, options = {}, timeoutMs = CHAT_TIMEOUT_MS) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(url, { ...options, signal: controller.signal })
    const responseText = await response.text()
    let data = {}

    if (responseText) {
      try {
        data = JSON.parse(responseText)
      } catch {
        throw new Error('The service returned an unreadable response.')
      }
    }

    if (!response.ok) {
      throw new Error(
        data.error || data.Message || 'The request could not be completed.',
      )
    }

    return data
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('The assistant took too long to respond. Please try again.', {
        cause: error,
      })
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

function SourceList({ sources }) {
  if (!sources?.length) return null

  return (
    <div className="source-list" aria-label="Sources used in this answer">
      <div className="source-heading">
        <FileText size={15} aria-hidden="true" />
        <span>{sources.length === 1 ? 'Source' : 'Sources'}</span>
      </div>
      {sources.map((source) => (
        <div
          className="source-row"
          key={`${source.id}-${source.path}`}
          title={source.path}
        >
          <span className="source-id">{source.id}</span>
          <span className="source-name">{sourceName(source.path)}</span>
          {source.timestamp && (
            <span className="source-time">{source.timestamp}</span>
          )}
        </div>
      ))}
    </div>
  )
}

function AssistantMessage({ message }) {
  return (
    <article className="message assistant-message">
      <div className="assistant-mark" aria-hidden="true">
        <Building2 size={17} />
      </div>
      <div className="message-content">
        <div className="message-label">CSUB Procurement Assistant</div>
        <div className="markdown">
          <ReactMarkdown>{message.text}</ReactMarkdown>
        </div>
        <SourceList sources={message.sources} />
      </div>
    </article>
  )
}

function App() {
  const [input, setInput] = useState('')
  const [role, setRole] = useState('requester')
  const [messages, setMessages] = useState([])
  const [isSending, setIsSending] = useState(false)
  const [serviceStatus, setServiceStatus] = useState('checking')
  const [serviceVersion, setServiceVersion] = useState('')
  const chatEndRef = useRef(null)
  const inputRef = useRef(null)
  const sendInFlightRef = useRef(false)

  useEffect(() => {
    let isCurrent = true

    fetchJson(HEALTH_API_URL, {}, HEALTH_TIMEOUT_MS)
      .then((health) => {
        if (!isCurrent) return
        if (health.status !== 'ok') {
          throw new Error('Unexpected health response.')
        }
        setServiceVersion(health.version || '')
        setServiceStatus('online')
      })
      .catch(() => {
        if (isCurrent) setServiceStatus('unavailable')
      })

    return () => {
      isCurrent = false
    }
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isSending])

  async function sendMessage(text = input) {
    const userText = text.trim()
    if (!userText || sendInFlightRef.current) return

    const history = messages.slice(-6).map(({ sender, text: messageText }) => ({
      role: sender,
      text: messageText,
    }))

    setInput('')
    sendInFlightRef.current = true
    setIsSending(true)
    setMessages((previous) => [
      ...previous,
      { id: crypto.randomUUID(), sender: 'user', text: userText },
    ])

    try {
      const data = await fetchJson(CHAT_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText, role, history }),
      })

      if (typeof data.answer !== 'string' || !data.answer.trim()) {
        throw new Error('The assistant returned an empty response.')
      }

      setServiceStatus('online')
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          sender: 'assistant',
          text: data.answer,
          sources: data.sources || [],
          requestId: data.request_id || '',
        },
      ])
    } catch (error) {
      setServiceStatus('unavailable')
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          sender: 'assistant',
          text:
            error instanceof Error
              ? `I could not connect to the assistant. ${error.message}`
              : 'I could not connect to the assistant. Please try again.',
          sources: [],
        },
      ])
    } finally {
      sendInFlightRef.current = false
      setIsSending(false)
      inputRef.current?.focus()
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    sendMessage()
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="brand-lockup">
          <img
            className="brand-logo"
            src={csubLogoHeader}
            alt="California State University Bakersfield"
          />
          <span className="brand-divider" aria-hidden="true" />
          <span className="product-name">Procurement Assistant</span>
        </div>
        <div className="header-meta">
          <span className="demo-badge">Standalone demo</span>
          <span
            className={`service-status is-${serviceStatus}`}
            title={
              serviceVersion
                ? `Connected to production backend version ${serviceVersion}`
                : 'Production backend connection status'
            }
            role="status"
          >
            <span className="status-dot" aria-hidden="true" />
            {serviceStatus === 'online'
              ? 'Assistant online'
              : serviceStatus === 'unavailable'
                ? 'Service unavailable'
                : 'Connecting'}
          </span>
        </div>
      </header>

      <main className="workspace">
        <section className="assistant-panel" aria-label="Procurement assistant">
          <div className="role-bar">
            <span className="role-label">I am a</span>
            <div className="role-options" aria-label="Choose your role">
              {roles.map(({ id, label, Icon }) => (
                <button
                  className={`role-option ${role === id ? 'is-active' : ''}`}
                  type="button"
                  key={id}
                  onClick={() => setRole(id)}
                  aria-pressed={role === id}
                >
                  <Icon size={16} aria-hidden="true" />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className={`conversation ${messages.length ? 'has-messages' : ''}`}>
            {messages.length === 0 ? (
              <div className="welcome">
                <div className="welcome-mark" aria-hidden="true">
                  <Building2 size={28} />
                </div>
                <p className="eyebrow">Purchasing guidance</p>
                <h1>What do you need help purchasing?</h1>

                <div className="starter-grid" aria-label="Suggested questions">
                  {starters.map(({ text, Icon }) => (
                    <button
                      className="starter"
                      type="button"
                      key={text}
                      onClick={() => sendMessage(text)}
                    >
                      <Icon size={19} aria-hidden="true" />
                      <span>{text}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="message-list" aria-live="polite">
                {messages.map((message) =>
                  message.sender === 'assistant' ? (
                    <AssistantMessage key={message.id} message={message} />
                  ) : (
                    <article className="message user-message" key={message.id}>
                      <div className="message-content">
                        <div className="message-label">You</div>
                        <p>{message.text}</p>
                      </div>
                    </article>
                  ),
                )}

                {isSending && (
                  <article className="message assistant-message loading-message">
                    <div className="assistant-mark" aria-hidden="true">
                      <Building2 size={17} />
                    </div>
                    <div className="message-content">
                      <div className="message-label">CSUB Procurement Assistant</div>
                      <div className="thinking" aria-label="Preparing an answer">
                        <span />
                        <span />
                        <span />
                      </div>
                    </div>
                  </article>
                )}
                <div ref={chatEndRef} />
              </div>
            )}
          </div>

          <form className="composer-area" onSubmit={handleSubmit}>
            <div className="composer">
              <textarea
                ref={inputRef}
                value={input}
                rows="1"
                maxLength="4000"
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    event.currentTarget.form?.requestSubmit()
                  }
                }}
                placeholder="Ask a procurement question"
                aria-label="Procurement question"
              />
              <button
                className="send-button"
                type="submit"
                disabled={!input.trim() || isSending}
                aria-label="Send question"
                title="Send question"
              >
                <ArrowUp size={20} strokeWidth={2.5} aria-hidden="true" />
              </button>
            </div>
            <p className="scope-note">
              Guidance only. This demo cannot access, submit, approve, or change
              live procurement records.
            </p>
          </form>
        </section>
      </main>
    </div>
  )
}

export default App
