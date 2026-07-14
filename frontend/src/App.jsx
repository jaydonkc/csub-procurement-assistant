import { useState } from 'react'
import './App.css'

function App() {
  const [input, setInput] = useState("")
  const[messages, setMessages] = useState([])
  async function sendMessage() {
    if (!input.trim()) return

    const userText = input
    setInput("")

    setMessages(prev => [...prev, { sender: "user", text: userText }
    ])

    const response = await fetch("http://127.0.0.1:5000/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json",},
      body: JSON.stringify({ message: userText }),
    })

    const data = await response.json()

    setMessages(prev => [...prev, { sender: "assistant", text: data.answer }
    ])
  }

  return (
    <div className="app">
      <h1>CSUB Procurement Assistant</h1>

      <div className="chat-box">
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
