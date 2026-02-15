import { useState, useRef, useImperativeHandle, forwardRef, useEffect } from 'react'
import { chatWithAgent } from '../services/api'
import DiagnosisCard from './DiagnosisCard'
import './ChatInterface.css'

const ChatInterface = forwardRef(function ChatInterface({ sessionId, location, initialInput, onDiagnosis }, ref) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'नमस्ते! मैं कृषि-सारथी हूँ 🌾\nमैं आपकी फसल की बीमारी पहचानने, इलाज बताने और नज़दीकी दुकान खोजने में मदद कर सकता हूँ।\n\nHow can I help you today?',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef()

  useEffect(() => {
    if (initialInput) setInput(initialInput)
  }, [initialInput])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useImperativeHandle(ref, () => ({
    sendMessage: (text) => { doSend(text) },
  }))

  async function doSend(text) {
    const msg = text || input
    if (!msg.trim()) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: msg }])
    setLoading(true)

    try {
      const res = await chatWithAgent(
        msg, sessionId, null,
        location?.lat, location?.lng, 'hi'
      )
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: res.reply || 'कोई जवाब नहीं मिला।',
          diagnosis: res.diagnosis,
          vendors: res.vendors,
        },
      ])
      if (res.diagnosis && onDiagnosis) onDiagnosis(res.diagnosis)
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', text: '⚠️ Error connecting to server. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <div className="msg-avatar">{m.role === 'user' ? '👨‍🌾' : '🤖'}</div>
            <div className="msg-bubble">
              <div className="msg-text">{m.text}</div>
              {m.diagnosis && <DiagnosisCard data={m.diagnosis} compact />}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-msg assistant">
            <div className="msg-avatar">🤖</div>
            <div className="msg-bubble">
              <div className="typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input-bar" onSubmit={(e) => { e.preventDefault(); doSend() }}>
        <input
          className="chat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="अपना सवाल पूछें... / Ask your question..."
          disabled={loading}
        />
        <button className="chat-send" type="submit" disabled={loading || !input.trim()}>
          ➤
        </button>
      </form>
    </div>
  )
})

export default ChatInterface
