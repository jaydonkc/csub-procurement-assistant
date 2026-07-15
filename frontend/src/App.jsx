import { useState, useEffect, useRef } from 'react'

function App() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [isSending, setIsSending] = useState(false)
  const chatBoxRef = useRef(null)

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight
    }
  }, [messages])

  async function sendMessage() {
    const userText = input.trim()
    if (!userText || isSending) return

    setInput('')
    setIsSending(true)

    setMessages((prev) => [...prev, { sender: 'user', text: userText }])

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userText,
        }),
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.error || 'Request failed')
      }

      setMessages((prev) => [...prev, { sender: 'assistant', text: data.answer }])
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: error.message || 'Error connecting to backend.',
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div className="app">
      <h1>CSUB Procurement Assistant</h1>

      <div className="chat-box" ref={chatBoxRef}>
        {messages.map((msg, index) => (
          <div key={index} className={msg.sender}>
            <strong>{msg.sender === 'user' ? 'You' : 'Assistant'}:</strong> {msg.text}
          </div>
        ))}
      </div>

      <div className="input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a procurement question..."
          onKeyDown={(e) => {
            if (e.key === 'Enter') sendMessage()
          }}
        />

        <button onClick={sendMessage} disabled={isSending}>
          {isSending ? 'Sending' : 'Send'}
        </button>
      </div>
    </div>
  )
}

export default App
