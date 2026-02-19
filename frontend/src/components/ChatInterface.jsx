import { useState, useRef, useImperativeHandle, forwardRef, useEffect } from 'react'
import { chatWithAgent } from '../services/api'
import DiagnosisCard from './DiagnosisCard'
import './ChatInterface.css'

/**
 * ChatInterface — controlled chat component.
 *
 * Props:
 *   messages        — array of { role, text, image_preview?, diagnosis? }
 *   sessionId       — current session id string
 *   location        — { lat, lng } or null
 *   initialInput    — pre-filled text input
 *   onDiagnosis     — callback(data, meta) when diagnosis received
 *   onAddMessage    — callback(role, text, extra) to add message to session
 *   onSetMessages   — callback(msgs) to replace all messages (for reset)
 */
const ChatInterface = forwardRef(function ChatInterface(
  { messages, sessionId, location, initialInput, onDiagnosis, onAddMessage, onSetMessages },
  ref
) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [answerLength, setAnswerLength] = useState('medium')
  const bottomRef = useRef()
  const fileRef = useRef()
  const [pendingImage, setPendingImage] = useState(null)
  const [pendingPreview, setPendingPreview] = useState(null)

  useEffect(() => { if (initialInput) setInput(initialInput) }, [initialInput])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  // Reset pending image when session changes
  useEffect(() => {
    setPendingImage(null)
    setPendingPreview(null)
  }, [sessionId])

  useImperativeHandle(ref, () => ({
    sendMessage: (text) => doSend(text),
  }))

  async function doSend(text) {
    const msg = (text || input).trim()
    if (!msg) return
    setInput('')
    onAddMessage('user', msg)
    setLoading(true)

    try {
      const res = await chatWithAgent(
        msg,
        sessionId,
        pendingImage,
        location?.lat,
        location?.lng,
        'hi',
        { answer_length: answerLength }
      )

      onAddMessage('assistant', res.reply || 'कोई जवाब नहीं मिला।', {
        diagnosis: res.diagnosis,
        vendors: res.vendors,
      })

      if (res.diagnosis && onDiagnosis) {
        onDiagnosis(res.diagnosis, { from: 'chat' })
      }
    } catch (e) {
      console.error(e)
      onAddMessage('assistant', '⚠️ Error connecting to server. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function openFilePicker() { fileRef.current?.click() }

  async function handleFileInput(e) {
    const file = e.target.files?.[0]
    if (!file) return
    await sendImageInChat(file)
    e.target.value = ''
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
      setPendingImage(b64)
      setPendingPreview(previewUrl)

      onAddMessage('user', '📷 Image uploaded', { image_preview: previewUrl })
      onAddMessage('assistant', 'Image received 🌿\nWhat would you like to know about this crop?')
    } catch (e) {
      console.error(e)
      onAddMessage('assistant', '⚠️ Failed to process image.')
    }
  }

  return (
    <div className="chat-container">
      {/* Chat header */}
      <div className="chat-header">
        <div className="chat-controls-left">
          {/* New Chat button removed — now handled by sidebar */}
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
                {m.image_preview && (
                  <img
                    src={m.image_preview}
                    alt="preview"
                    style={{ maxWidth: 220, borderRadius: 6, marginBottom: 6 }}
                  />
                )}
                {m.text}
              </div>
              {m.diagnosis &&
                (m.diagnosis.disease || m.diagnosis.top_disease) &&
                m.diagnosis.disease !== 'Unknown' && (
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
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileInput}
          hidden
        />
        <button type="button" className="chat-upload" onClick={openFilePicker} title="Upload photo">
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
