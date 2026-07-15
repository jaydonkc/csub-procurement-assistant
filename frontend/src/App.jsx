import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  ArrowUp,
  Building2,
  Clock3,
  CirclePlay,
  ExternalLink,
  FileText,
  FileVideo2,
  Headphones,
  Laptop,
  PackageCheck,
  Store,
  UserRound,
  UserRoundCog,
  X,
} from 'lucide-react'
import csubLogoHeader from './assets/csub-logo-header.png'

const DEFAULT_API_BASE_URL =
  'https://w0vfga8dil.execute-api.us-west-2.amazonaws.com/prod'
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/+$/, '')
const CHAT_API_URL = import.meta.env.VITE_API_URL || `${API_BASE_URL}/v1/chat`
const CHAT_TIMEOUT_MS = 32_000

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

function sourceKey(source) {
  return `${source.id}-${source.path}-${source.timestamp || ''}`
}

function isVideoSource(source) {
  return (
    source.kind === 'video_transcript' ||
    source.path?.toLowerCase().endsWith('.mp4')
  )
}

function timestampToSeconds(timestamp) {
  const match = /^(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)$/.exec(timestamp?.trim())
  if (!match) return null
  return Number(match[1]) * 3600 + Number(match[2]) * 60 + Number(match[3])
}

function parseTimestampRange(timestamp = '') {
  const [startLabel, endLabel] = (timestamp || '').split(/\s*-->\s*/)
  const start = timestampToSeconds(startLabel)
  const end = timestampToSeconds(endLabel)
  return {
    start,
    end,
    startLabel: start === null ? '' : startLabel,
    endLabel: end === null ? '' : endLabel,
  }
}

function formatPlaybackTime(seconds) {
  if (!Number.isFinite(seconds)) return ''
  const wholeSeconds = Math.floor(seconds)
  const hours = Math.floor(wholeSeconds / 3600)
  const minutes = Math.floor((wholeSeconds % 3600) / 60)
  const remainder = wholeSeconds % 60
  return hours
    ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
    : `${minutes}:${String(remainder).padStart(2, '0')}`
}

function playbackUrl(source, range) {
  const sourceUrl = source.source_url || source.media_url
  if (!sourceUrl) return ''
  const baseUrl = sourceUrl.split('#')[0]
  if (range.start === null) return baseUrl
  const start = range.start.toFixed(3)
  const end = range.end === null ? '' : `,${range.end.toFixed(3)}`
  return `${baseUrl}#t=${start}${end}`
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

function SourceList({ sources, onSelectSource, selectedSourceKey }) {
  if (!sources?.length) return null

  return (
    <div className="source-list" aria-label="Sources used in this answer">
      <div className="source-heading">
        <FileText size={15} aria-hidden="true" />
        <span>{sources.length === 1 ? 'Source' : 'Sources'}</span>
      </div>
      <div className="source-items">
        {sources.map((source) => {
          const key = sourceKey(source)
          const videoSource = isVideoSource(source)
          const SourceIcon = videoSource ? FileVideo2 : FileText
          const href = videoSource ? '' : source.source_url || source.media_url || ''
          const content = (
            <>
              <SourceIcon size={16} aria-hidden="true" />
              <span className="source-copy">
                <span className="source-title-row">
                  <span className="source-id">{source.id}</span>
                  <span className="source-name">{sourceName(source.path)}</span>
                </span>
                {source.timestamp && (
                  <span className="source-time">{source.timestamp}</span>
                )}
              </span>
              {videoSource ? (
                <CirclePlay size={16} aria-hidden="true" />
              ) : (
                <ExternalLink size={16} aria-hidden="true" />
              )}
            </>
          )

          if (href) {
            return (
              <a
                className={`source-row ${selectedSourceKey === key ? 'is-active' : ''}`}
                href={href}
                key={key}
                target="_blank"
                rel="noopener noreferrer"
                referrerPolicy="no-referrer"
                title={`Open ${source.path} in a new tab`}
                onClick={() => onSelectSource(source)}
                aria-current={selectedSourceKey === key ? 'true' : undefined}
              >
                {content}
              </a>
            )
          }

          return (
            <button
              className={`source-row ${selectedSourceKey === key ? 'is-active' : ''}`}
              key={key}
              type="button"
              title={`Preview ${source.path}`}
              onClick={() => onSelectSource(source)}
              aria-pressed={selectedSourceKey === key}
            >
              {content}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function SourcePanel({ source, onClose }) {
  const range = parseTimestampRange(source.timestamp)
  const videoSource = isVideoSource(source)
  const videoUrl = playbackUrl(source, range)
  const externalUrl = videoSource
    ? videoUrl
    : source.source_url || source.media_url || ''

  function preloadTimestamp(event) {
    if (range.start === null) return
    const player = event.currentTarget
    const lastSeekableSecond = Number.isFinite(player.duration)
      ? Math.max(player.duration - 0.01, 0)
      : range.start
    player.currentTime = Math.min(range.start, lastSeekableSecond)
  }

  return (
    <aside className="source-panel" aria-labelledby="source-panel-title">
      <div className="source-panel-header">
        <div>
          <span className="source-kicker">Source {source.id}</span>
          <h2 id="source-panel-title">{sourceName(source.path)}</h2>
        </div>
        <div className="source-panel-actions">
          {externalUrl && (
            <a
              className="source-open"
              href={externalUrl}
              target="_blank"
              rel="noopener noreferrer"
              referrerPolicy="no-referrer"
              aria-label={`Open ${sourceName(source.path)} in a new tab`}
              title="Open in new tab"
            >
              <ExternalLink size={19} aria-hidden="true" />
            </a>
          )}
          <button
            className="source-close"
            type="button"
            onClick={onClose}
            aria-label="Close source panel"
            title="Close source panel"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="source-panel-body">
        {videoSource ? (
          <>
            {videoUrl ? (
              <video
                className="source-video"
                key={videoUrl}
                src={videoUrl}
                controls
                playsInline
                preload="metadata"
                onLoadedMetadata={preloadTimestamp}
                aria-label={`Video source: ${sourceName(source.path)}`}
              />
            ) : (
              <div className="video-unavailable">
                <FileVideo2 size={28} aria-hidden="true" />
                <span>Video preview is unavailable.</span>
              </div>
            )}

            {range.start !== null && (
              <div className="segment-callout">
                <Clock3 size={17} aria-hidden="true" />
                <div>
                  <span>Cited segment</span>
                  <strong>
                    {formatPlaybackTime(range.start)}
                    {range.end !== null && ` - ${formatPlaybackTime(range.end)}`}
                  </strong>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="document-preview">
            <FileText size={30} aria-hidden="true" />
            <span>Document source</span>
          </div>
        )}

        <div className="source-details">
          <span>Source path</span>
          <p>{source.path}</p>
        </div>
      </div>
    </aside>
  )
}

function AssistantMessage({
  message,
  onSelectSource,
  selectedSourceKey,
}) {
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
        <SourceList
          sources={message.sources}
          onSelectSource={onSelectSource}
          selectedSourceKey={selectedSourceKey}
        />
      </div>
    </article>
  )
}

function App() {
  const [input, setInput] = useState('')
  const [role, setRole] = useState('requester')
  const [messages, setMessages] = useState([])
  const [isSending, setIsSending] = useState(false)
  const [selectedSource, setSelectedSource] = useState(null)
  const chatEndRef = useRef(null)
  const inputRef = useRef(null)
  const sendInFlightRef = useRef(false)

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
    setSelectedSource(null)
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
      </header>

      <main className="workspace">
        <section
          className={`assistant-panel ${selectedSource ? 'has-source-panel' : ''}`}
          aria-label="Procurement assistant"
        >
          <div className="assistant-main">
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
                    <AssistantMessage
                      key={message.id}
                      message={message}
                      onSelectSource={setSelectedSource}
                      selectedSourceKey={
                        selectedSource ? sourceKey(selectedSource) : ''
                      }
                    />
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
          </div>

          {selectedSource && (
            <SourcePanel
              source={selectedSource}
              onClose={() => setSelectedSource(null)}
            />
          )}
        </section>
      </main>
    </div>
  )
}

export default App
