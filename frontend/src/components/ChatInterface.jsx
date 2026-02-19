import { useState, useRef, useImperativeHandle, forwardRef, useEffect } from 'react'
import { chatWithAgent, diagnoseImage } from '../services/api'
import DiagnosisCard from './DiagnosisCard'
import './ChatInterface.css'

const DEFAULT_WELCOME = {
  role: 'assistant',
  text:
    'नमस्ते! मैं कृषि-सारथी हूँ 🌾\nमैं आपकी फसल की बीमारी पहचानने, इलाज बताने और नज़दीकी दुकान खोजने में मदद कर सकता हूँ।\n\nHow can I help you today?',
}

const ChatInterface = forwardRef(function ChatInterface({ sessionId, location, initialInput, onDiagnosis }, ref) {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('chat_history')
    return saved ? JSON.parse(saved) : [DEFAULT_WELCOME]
  })
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [answerLength, setAnswerLength] = useState('medium') // short | medium | long
  const bottomRef = useRef()
  const fileRef = useRef()
  const [currentSessionId, setCurrentSessionId] = useState(() => sessionId || localStorage.getItem('chat_session_id') || `session-${Date.now()}`)
  const [pendingImage, setPendingImage] = useState(null)
  const [pendingPreview, setPendingPreview] = useState(null)
  
  // persist messages & session id
  useEffect(() => { localStorage.setItem('chat_history', JSON.stringify(messages)) }, [messages])
  useEffect(() => { if (currentSessionId) localStorage.setItem('chat_session_id', currentSessionId) }, [currentSessionId])
  useEffect(() => { if (initialInput) setInput(initialInput) }, [initialInput])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  useImperativeHandle(ref, () => ({ sendMessage: (text) => { doSend(text) } }))

  function resetChat() {
    const newSession = `session-${Date.now()}`
    setMessages([DEFAULT_WELCOME])
    setInput('')
    setCurrentSessionId(newSession)
  
    // clear stored image
    setPendingImage(null)
    setPendingPreview(null)
  
    localStorage.removeItem('chat_history')
    localStorage.setItem('chat_session_id', newSession)
  }
  

  async function doSend(text) {
    const msg = (text || input).trim()
    if (!msg) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: msg }])
    setLoading(true)

    try {
      const activeSessionId = currentSessionId
      // pass answer length preference to backend. Backend may ignore if not implemented.
      const res = await chatWithAgent(
        msg,
        activeSessionId,
        pendingImage, // send stored image
        location?.lat,
        location?.lng,
        'hi',
        { answer_length: answerLength }
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
      if (res.diagnosis && onDiagnosis) {
        // indicate origin is chat so Dashboard doesn't auto-open Results
        onDiagnosis(res.diagnosis, { from: 'chat' })
      }
      // clear image after sending
      // setPendingImage(null)
      // setPendingPreview(null)

    } catch (e) {
      console.error(e)
      setMessages((prev) => [...prev, { role: 'assistant', text: '⚠️ Error connecting to server. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  // file / camera upload handler in-chat
  function openFilePicker() { fileRef.current?.click() }

  async function handleFileInput(e) {
    const file = e.target.files?.[0]
    if (!file) return
    await sendImageInChat(file)
    e.target.value = '' // reset
  }

  async function sendImageInChat(file) {
    try {
      const b64 = await new Promise((res, rej) => {
        const reader = new FileReader()
        reader.onload = () => res(reader.result.split(',')[1])
        reader.onerror = rej
        reader.readAsDataURL(file)
      })
  
      const previewUrl = URL.createObjectURL(file)
  
      // store image but DO NOT send yet
      setPendingImage(b64)
      setPendingPreview(previewUrl)
  
      setMessages((prev) => [
        ...prev,
        { role: 'user', text: '📷 Image uploaded', image_preview: previewUrl },
        { role: 'assistant', text: 'Image received 🌿\nWhat would you like to know about this crop?' }
      ])
    } catch (e) {
      console.error(e)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: '⚠️ Failed to process image.' }
      ])
    }
  }
  

  return (
    <div className="chat-container">
      {/* Chat header with controls */}
      <div className="chat-header">
        <div className="chat-controls-left">
          <button className="btn-reset" onClick={resetChat} title="Start new chat">🔁 New Chat</button>
        </div>
        <div className="chat-controls-right">
          <label className="answer-length">
            Length:
            <select value={answerLength} onChange={(e) => setAnswerLength(e.target.value)}>
              <option value="short">Short</option>
              <option value="medium">Medium</option>
              <option value="long">Long</option>
            </select>
          </label>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <div className="msg-avatar">{m.role === 'user' ? '👨‍🌾' : '🤖'}</div>
            <div className="msg-bubble">
              <div className="msg-text">
                {m.image_preview && <img src={m.image_preview} alt="preview" style={{ maxWidth: 220, borderRadius: 6, marginBottom: 6 }} />}
                {m.text}
              </div>
              {m.diagnosis && 
                (m.diagnosis.disease || m.diagnosis.top_disease) &&
                (m.diagnosis.disease !== 'Unknown') &&
                (
                  <DiagnosisCard data={m.diagnosis} compact />
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-msg assistant">
            <div className="msg-avatar">🤖</div>
            <div className="msg-bubble">
              <div className="typing-indicator"><span /><span /><span /></div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      {pendingPreview && (
        <div style={{ padding: 8, fontSize: 14, color: '#4caf50' }}>
          📷 Image attached — will be sent with your next message
        </div>
      )}

      <form className="chat-input-bar" onSubmit={(e) => { e.preventDefault(); doSend() }}>
        <input
          className="chat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="अपना सवाल पूछें... / Ask your question..."
          disabled={loading}
        />

        {/* File / Camera input for quick image upload */}
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileInput}
          hidden
        />
        <button type="button" className="chat-upload" onClick={openFilePicker} title="Upload photo (camera)">
          📷
        </button>

        <button className="chat-send" type="submit" disabled={loading || !input.trim()}>
          ➤
        </button>
      </form>
    </div>
  )
})

export default ChatInterface
