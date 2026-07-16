import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  ArrowUp,
  Building2,
  Check,
  Clock3,
  CirclePlay,
  ClipboardList,
  ExternalLink,
  FileText,
  FileVideo2,
  Headphones,
  Laptop,
  PackageCheck,
  PanelRightOpen,
  Plus,
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
const DEFAULT_SOURCE_PANEL_PERCENT = 42
const MIN_SOURCE_PANEL_WIDTH = 280
const MIN_CHAT_PANEL_WIDTH = 320
const SOURCE_PANEL_MAX_PERCENT = 64
const RESIZER_WIDTH = 9

const roles = [
  { id: 'requester', label: 'Faculty or Staff', Icon: UserRound },
  { id: 'vendor', label: 'Vendor or Supplier', Icon: Store },
  { id: 'internal_staff', label: 'Support Staff', Icon: Headphones },
]

const startersByRole = {
  requester: [
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
  ],
  vendor: [
    {
      text: 'How do I complete supplier registration after receiving an invitation?',
      Icon: Store,
    },
    {
      text: 'What information should I include with an invoice?',
      Icon: FileText,
    },
    {
      text: 'How do I check the status of an invoice or payment?',
      Icon: Clock3,
    },
    {
      text: 'Who should I contact if supplier onboarding is stalled?',
      Icon: Headphones,
    },
  ],
  internal_staff: [
    {
      text: 'How do I help a requester find or request a supplier?',
      Icon: Store,
    },
    {
      text: 'Where do I submit a CSUBUY support ticket?',
      Icon: Headphones,
    },
    {
      text: 'How do I explain voucher pay status?',
      Icon: Clock3,
    },
    {
      text: 'What public guidance can I share for updating a CSUBUY profile?',
      Icon: UserRoundCog,
    },
  ],
}

function createEmptyRoleSession() {
  return {
    input: '',
    messages: [],
    isSending: false,
    selectedSource: null,
    selectedStatus: null,
  }
}

function createRoleSessions() {
  return Object.fromEntries(
    roles.map(({ id }) => [id, createEmptyRoleSession()]),
  )
}

function sourceName(path = 'CSUB procurement source') {
  return path.split('/').pop() || path
}

function sourceKey(source) {
  return `${source.id}-${source.path}-${source.timestamp || ''}`
}

function statusKey(status) {
  return status?.record_id || ''
}

function isVideoSource(source) {
  return (
    source.kind === 'video_transcript' ||
    source.path?.toLowerCase().endsWith('.mp4')
  )
}

function isPdfSource(source) {
  return source.path?.toLowerCase().endsWith('.pdf')
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

function formatTimestampRange(timestamp) {
  const range = parseTimestampRange(timestamp)
  if (range.start === null) return timestamp
  const start = formatPlaybackTime(range.start)
  const end = range.end === null ? '' : ` --> ${formatPlaybackTime(range.end)}`
  return `${start}${end}`
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
          const content = (
            <>
              <SourceIcon size={16} aria-hidden="true" />
              <span className="source-copy">
                <span className="source-title-row">
                  <span className="source-id">{source.id}</span>
                  <span className="source-name">{sourceName(source.path)}</span>
                </span>
                {source.timestamp && (
                  <span className="source-time">
                    {formatTimestampRange(source.timestamp)}
                  </span>
                )}
              </span>
              {videoSource ? (
                <CirclePlay size={16} aria-hidden="true" />
              ) : (
                <PanelRightOpen size={16} aria-hidden="true" />
              )}
            </>
          )

          return (
            <button
              className={`source-row ${selectedSourceKey === key ? 'is-active' : ''}`}
              key={key}
              type="button"
              title={`View ${source.path}`}
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
  const [captionState, setCaptionState] = useState(
    source.caption_url ? 'loading' : 'missing',
  )
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

  function markCaptionsReady() {
    setCaptionState('ready')
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
                key={`${videoUrl}-${source.caption_url || ''}`}
                crossOrigin={source.caption_url ? 'anonymous' : undefined}
                src={videoUrl}
                controls
                playsInline
                preload="metadata"
                onLoadedMetadata={preloadTimestamp}
                aria-label={`Video source: ${sourceName(source.path)}`}
              >
                {source.caption_url && (
                  <track
                    kind="captions"
                    src={source.caption_url}
                    srcLang="en"
                    label="English"
                    onLoad={markCaptionsReady}
                    onError={() => setCaptionState('error')}
                  />
                )}
              </video>
            ) : (
              <div className="video-unavailable">
                <FileVideo2 size={28} aria-hidden="true" />
                <span>Video preview is unavailable.</span>
              </div>
            )}

            {videoUrl && ['missing', 'error'].includes(captionState) && (
              <p className="caption-status" role="status">
                Closed captions are temporarily unavailable. The cited answer
                provides a readable transcript summary.
              </p>
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
        ) : isPdfSource(source) && externalUrl ? (
          <iframe
            className="source-pdf"
            key={externalUrl}
            src={externalUrl}
            title={`PDF source: ${sourceName(source.path)}`}
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="document-preview">
            <FileText size={30} aria-hidden="true" />
            <span>Preview unavailable for this file type.</span>
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

function StatusResult({ status, onSelectStatus, isActive }) {
  if (!status) return null

  return (
    <div className="status-result" aria-label="Transaction status result">
      <div className="source-heading">
        <ClipboardList size={15} aria-hidden="true" />
        <span>Status details</span>
      </div>
      <button
        className={`status-result-button ${isActive ? 'is-active' : ''}`}
        type="button"
        onClick={() => onSelectStatus(status)}
        aria-pressed={isActive}
      >
        <span className="status-result-icon" aria-hidden="true">
          <ClipboardList size={18} />
        </span>
        <span className="status-result-copy">
          <strong>{status.record_id}</strong>
          <span>{status.status}</span>
        </span>
        <PanelRightOpen size={17} aria-hidden="true" />
      </button>
    </div>
  )
}

function StatusPanel({ status, onClose }) {
  const stages = Array.isArray(status.stages) ? status.stages : []
  const fields = Array.isArray(status.fields) ? status.fields : []

  return (
    <aside
      className="source-panel status-panel"
      aria-labelledby="status-panel-title"
    >
      <div className="source-panel-header status-panel-header">
        <div>
          <span className="source-kicker">Status</span>
          <h2 id="status-panel-title">{status.record_id}</h2>
        </div>
        <div className="source-panel-actions">
          <button
            className="source-close"
            type="button"
            onClick={onClose}
            aria-label="Close status panel"
            title="Close status panel"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="source-panel-body status-panel-body">
        <div className="status-summary">
          <span className="status-record-type">{status.record_type}</span>
          <h3>{status.title}</h3>
          <span className="status-current">{status.status}</span>
          <span className="status-updated">Updated {status.last_updated}</span>
        </div>

        <section className="status-progress" aria-labelledby="status-progress-title">
          <div className="status-section-heading">
            <span id="status-progress-title">Progress</span>
            <strong>
              Step {status.current_stage} of {stages.length}
            </strong>
          </div>
          <ol
            className="status-steps"
            style={{ '--stage-count': stages.length }}
          >
            {stages.map((stage, index) => {
              const step = index + 1
              const state =
                step < status.current_stage
                  ? 'complete'
                  : step === status.current_stage
                    ? 'current'
                    : 'upcoming'
              return (
                <li className={`status-step is-${state}`} key={stage}>
                  <span className="status-step-marker" aria-hidden="true">
                    {state === 'complete' ? <Check size={14} /> : step}
                  </span>
                  <span className="status-step-label">{stage}</span>
                </li>
              )
            })}
          </ol>
        </section>

        <section className="status-field-section" aria-labelledby="status-fields-title">
          <div className="status-section-heading">
            <span id="status-fields-title">Record details</span>
          </div>
          <dl className="status-fields">
            {fields.map((field) => (
              <div key={field.label}>
                <dt>{field.label}</dt>
                <dd>{field.value}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="status-next-step" aria-labelledby="status-next-title">
          <span id="status-next-title">What happens next</span>
          <p>{status.next_step}</p>
        </section>

      </div>
    </aside>
  )
}

function AssistantMessage({
  message,
  onSelectSource,
  onSelectStatus,
  selectedSourceKey,
  selectedStatusKey,
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
        <StatusResult
          status={message.statusCard}
          onSelectStatus={onSelectStatus}
          isActive={selectedStatusKey === statusKey(message.statusCard)}
        />
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
  const [role, setRole] = useState('requester')
  const [roleSessions, setRoleSessions] = useState(createRoleSessions)
  const [sourcePanelPercent, setSourcePanelPercent] = useState(
    DEFAULT_SOURCE_PANEL_PERCENT,
  )
  const [isResizingSource, setIsResizingSource] = useState(false)
  const assistantPanelRef = useRef(null)
  const isResizingSourceRef = useRef(false)
  const chatEndRef = useRef(null)
  const inputRef = useRef(null)
  const activeRoleRef = useRef(role)
  const sendInFlightRef = useRef(
    Object.fromEntries(roles.map(({ id }) => [id, false])),
  )
  const { input, messages, isSending, selectedSource, selectedStatus } =
    roleSessions[role]
  const hasDetailPanel = Boolean(selectedSource || selectedStatus)
  const starters = startersByRole[role]

  function setRoleSessionField(targetRole, field, nextValue) {
    setRoleSessions((previous) => {
      const currentSession = previous[targetRole]
      const value =
        typeof nextValue === 'function'
          ? nextValue(currentSession[field])
          : nextValue
      return {
        ...previous,
        [targetRole]: {
          ...currentSession,
          [field]: value,
        },
      }
    })
  }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isSending])

  async function sendMessage(text = input) {
    const requestRole = role
    const userText = text.trim()
    if (!userText || sendInFlightRef.current[requestRole]) return

    const history = roleSessions[requestRole].messages
      .slice(-6)
      .map(({ sender, text: messageText }) => ({
        role: sender,
        text: messageText,
      }))

    sendInFlightRef.current[requestRole] = true
    setRoleSessions((previous) => {
      const currentSession = previous[requestRole]
      return {
        ...previous,
        [requestRole]: {
          ...currentSession,
          input: '',
          selectedSource: null,
          selectedStatus: null,
          isSending: true,
          messages: [
            ...currentSession.messages,
            { id: crypto.randomUUID(), sender: 'user', text: userText },
          ],
        },
      }
    })

    try {
      const data = await fetchJson(CHAT_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText, role: requestRole, history }),
      })

      if (typeof data.answer !== 'string' || !data.answer.trim()) {
        throw new Error('The assistant returned an empty response.')
      }

      const sources = Array.isArray(data.sources) ? data.sources : []
      const statusCard =
        data.status_card && typeof data.status_card === 'object'
          ? data.status_card
          : null

      setRoleSessionField(requestRole, 'messages', (previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          sender: 'assistant',
          text: data.answer,
          sources,
          statusCard,
          requestId: data.request_id || '',
        },
      ])
      setRoleSessionField(
        requestRole,
        'selectedSource',
        statusCard ? null : sources[0] || null,
      )
      setRoleSessionField(requestRole, 'selectedStatus', statusCard)
    } catch (error) {
      setRoleSessionField(requestRole, 'messages', (previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          sender: 'assistant',
          text:
            error instanceof Error
              ? `I could not connect to the assistant. ${error.message}`
              : 'I could not connect to the assistant. Please try again.',
          sources: [],
          statusCard: null,
        },
      ])
    } finally {
      sendInFlightRef.current[requestRole] = false
      setRoleSessionField(requestRole, 'isSending', false)
      if (activeRoleRef.current === requestRole) {
        inputRef.current?.focus()
      }
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    sendMessage()
  }

  function handleNewChat() {
    setRoleSessions((previous) => ({
      ...previous,
      [role]: createEmptyRoleSession(),
    }))
    setSourcePanelPercent(DEFAULT_SOURCE_PANEL_PERCENT)
    inputRef.current?.focus()
  }

  function handleRoleChange(nextRole) {
    activeRoleRef.current = nextRole
    setRole(nextRole)
  }

  function handleSelectSource(source) {
    setRoleSessionField(role, 'selectedStatus', null)
    setRoleSessionField(role, 'selectedSource', (currentSource) =>
      currentSource && sourceKey(currentSource) === sourceKey(source)
        ? null
        : source,
    )
  }

  function handleSelectStatus(status) {
    setRoleSessionField(role, 'selectedSource', null)
    setRoleSessionField(role, 'selectedStatus', (currentStatus) =>
      statusKey(currentStatus) === statusKey(status) ? null : status,
    )
  }

  function setSourceWidthFromPixels(requestedWidth) {
    const panel = assistantPanelRef.current
    if (!panel) return

    const panelWidth = panel.getBoundingClientRect().width
    const maximumWidth = Math.min(
      panelWidth * (SOURCE_PANEL_MAX_PERCENT / 100),
      panelWidth - MIN_CHAT_PANEL_WIDTH - RESIZER_WIDTH,
    )
    const sourceWidth = Math.min(
      Math.max(maximumWidth, MIN_SOURCE_PANEL_WIDTH),
      Math.max(requestedWidth, MIN_SOURCE_PANEL_WIDTH),
    )

    setSourcePanelPercent((sourceWidth / panelWidth) * 100)
  }

  function resizeSourcePanel(clientX) {
    const panel = assistantPanelRef.current
    if (!panel) return

    const bounds = panel.getBoundingClientRect()
    setSourceWidthFromPixels(bounds.right - clientX)
  }

  function handleResizeKeyDown(event) {
    const panel = assistantPanelRef.current
    if (!panel) return

    const panelWidth = panel.getBoundingClientRect().width
    const currentWidth = panelWidth * (sourcePanelPercent / 100)

    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      setSourceWidthFromPixels(currentWidth + 24)
    } else if (event.key === 'ArrowRight') {
      event.preventDefault()
      setSourceWidthFromPixels(currentWidth - 24)
    } else if (event.key === 'Home') {
      event.preventDefault()
      setSourceWidthFromPixels(MIN_SOURCE_PANEL_WIDTH)
    } else if (event.key === 'End') {
      event.preventDefault()
      setSourceWidthFromPixels(panelWidth)
    }
  }

  function handleMouseResizeStart(event) {
    event.preventDefault()
    isResizingSourceRef.current = true
    assistantPanelRef.current?.classList.add('is-resizing-source')
    setIsResizingSource(true)
    resizeSourcePanel(event.clientX)

    function handleMouseMove(moveEvent) {
      resizeSourcePanel(moveEvent.clientX)
    }

    function stopMouseResize() {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', stopMouseResize)
      isResizingSourceRef.current = false
      assistantPanelRef.current?.classList.remove('is-resizing-source')
      setIsResizingSource(false)
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', stopMouseResize)
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
          ref={assistantPanelRef}
          className={`assistant-panel ${hasDetailPanel ? 'has-detail-panel' : ''} ${isResizingSource ? 'is-resizing-source' : ''}`}
          style={
            hasDetailPanel
              ? { '--source-panel-width': `${sourcePanelPercent}%` }
              : undefined
          }
          aria-label="Procurement assistant"
        >
          <div className="assistant-main">
            <div className="role-bar">
              <button
                className="new-chat-button"
                type="button"
                onClick={handleNewChat}
                disabled={isSending}
                aria-label="Start a new chat"
                title="Start a new chat"
              >
                <Plus size={17} aria-hidden="true" />
                <span className="new-chat-label">New chat</span>
              </button>
              <div className="role-controls">
                <span className="role-label">I am a</span>
                <div className="role-options" aria-label="Choose your role">
                  {roles.map(({ id, label, Icon }) => (
                    <button
                      className={`role-option ${role === id ? 'is-active' : ''}`}
                      type="button"
                      key={id}
                      onClick={() => handleRoleChange(id)}
                      aria-pressed={role === id}
                    >
                      <Icon size={16} aria-hidden="true" />
                      <span>{label}</span>
                    </button>
                  ))}
                </div>
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
                      onSelectSource={handleSelectSource}
                      onSelectStatus={handleSelectStatus}
                      selectedSourceKey={
                        selectedSource ? sourceKey(selectedSource) : ''
                      }
                      selectedStatusKey={statusKey(selectedStatus)}
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
                onChange={(event) =>
                  setRoleSessionField(role, 'input', event.target.value)
                }
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
              Guidance only. This assistant cannot access, submit, approve, or change
              live procurement records.
            </p>
            </form>
          </div>

          {hasDetailPanel && (
            <>
              <div
                className="source-resizer"
                role="separator"
                tabIndex="0"
                aria-label={`Resize ${selectedStatus ? 'status' : 'source'} panel`}
                aria-orientation="vertical"
                aria-valuemin={Math.round(
                  (MIN_SOURCE_PANEL_WIDTH /
                    (assistantPanelRef.current?.getBoundingClientRect().width ||
                      MIN_SOURCE_PANEL_WIDTH)) *
                    100,
                )}
                aria-valuemax={SOURCE_PANEL_MAX_PERCENT}
                aria-valuenow={Math.round(sourcePanelPercent)}
                onMouseDown={handleMouseResizeStart}
                onPointerDown={(event) => {
                  isResizingSourceRef.current = true
                  if (event.nativeEvent.isTrusted) {
                    event.currentTarget.setPointerCapture(event.pointerId)
                  }
                  setIsResizingSource(true)
                  resizeSourcePanel(event.clientX)
                }}
                onPointerMove={(event) => {
                  if (isResizingSourceRef.current) {
                    resizeSourcePanel(event.clientX)
                  }
                }}
                onPointerUp={(event) => {
                  if (
                    event.nativeEvent.isTrusted &&
                    event.currentTarget.hasPointerCapture(event.pointerId)
                  ) {
                    event.currentTarget.releasePointerCapture(event.pointerId)
                  }
                  isResizingSourceRef.current = false
                  setIsResizingSource(false)
                }}
                onPointerCancel={() => {
                  isResizingSourceRef.current = false
                  setIsResizingSource(false)
                }}
                onKeyDown={handleResizeKeyDown}
              />
              {selectedStatus ? (
                <StatusPanel
                  status={selectedStatus}
                  onClose={() =>
                    setRoleSessionField(role, 'selectedStatus', null)
                  }
                />
              ) : (
                <SourcePanel
                  key={`${sourceKey(selectedSource)}-${selectedSource.caption_url || ''}`}
                  source={selectedSource}
                  onClose={() =>
                    setRoleSessionField(role, 'selectedSource', null)
                  }
                />
              )}
            </>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
