import { useState, useEffect, useRef } from 'react'
import './App.css'

function App() {
  const [input, setInput] = useState("")
  const[messages, setMessages] = useState([])
  const chatBoxRef = useRef(null)
    useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight
    }
  }, [messages])
  async function sendMessage() {
    if (!input.trim()) return

    const userText = input
    setInput("")

    setMessages(prev => [...prev, { sender: "user", text: userText }])

    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userText,
        }),
      })

      console.log("Response status:", response.status)

      const data = await response.json()
      console.log("Backend response:", data)

      // Add the assistant's response
      setMessages(prev => [...prev, { sender: "assistant", text: data.answer }])
    } catch (error) {
      console.error("Error calling backend:", error)

      setMessages(prev => [...prev,{sender: "assistant", text: "Error connecting to backend.",},])
    }
  }

  return (
    <div className="app">
      <h1>CSUB Procurement Assistant</h1>

      <div className="chat-box" ref={chatBoxRef}>
        {messages.map((msg, index) => (
          <div key={index} className={msg.sender}>
            <strong>{msg.sender === "user" ? "You" : "Assistant"}:</strong> {msg.text}
          </div>
        ))}
      </div>

      <div className="input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a procurement question..."
          onKeyDown={(e) => {
            if (e.key === "Enter") sendMessage()
          }}
        />

        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  )
}

export default App
