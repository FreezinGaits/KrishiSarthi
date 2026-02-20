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
  const cameraRef = useRef()
  const [pendingImage, setPendingImage] = useState(null)
  const [pendingPreview, setPendingPreview] = useState(null)
  const [speakingId, setSpeakingId] = useState(null)

  // ── Text-to-Speech ─────────────────────────────
  function handleSpeak(text, msgIndex) {
    const synth = window.speechSynthesis
    if (!synth) return

    // If already speaking this message, stop it
    if (speakingId === msgIndex) {
      synth.cancel()
      setSpeakingId(null)
      return
    }

    // Stop any ongoing speech
    synth.cancel()

    // Clean text: strip emoji, markdown bold, etc.
    const clean = text
      .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '')
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/#{1,6}\s/g, '')
      .trim()

    const utter = new SpeechSynthesisUtterance(clean)
    utter.lang = 'hi-IN'
    utter.rate = 0.95
    utter.pitch = 1.0

    // Try to pick a Hindi voice
    const voices = synth.getVoices()
    const hindiVoice = voices.find((v) => v.lang.startsWith('hi'))
    if (hindiVoice) utter.voice = hindiVoice

    utter.onend = () => setSpeakingId(null)
    utter.onerror = () => setSpeakingId(null)

    setSpeakingId(msgIndex)
    synth.speak(utter)
  }

  // Cancel speech on session switch
  useEffect(() => {
    window.speechSynthesis?.cancel()
    setSpeakingId(null)
  }, [sessionId])

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

    // Capture and clear pending image so follow-up messages don't re-send it
    const imageToSend = pendingImage
    setPendingImage(null)
    setPendingPreview(null)

    console.log('[ChatInterface] doSend:', {
      msg: msg.substring(0, 60),
      hasImage: !!imageToSend,
      imageLen: imageToSend?.length || 0,
    })

    try {
      const res = await chatWithAgent(
        msg,
        sessionId,
        imageToSend,
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
  function openCamera() { cameraRef.current?.click() }

  async function handleFileInput(e) {
    const file = e.target.files?.[0]
    if (!file) return
    await sendImageInChat(file)
    e.target.value = ''
  }

  async function sendImageInChat(file) {
    try {
      // Read as data URL (base64) — this survives localStorage unlike blob URLs
      const dataUrl = await new Promise((res, rej) => {
        const reader = new FileReader()
        reader.onload = () => res(reader.result)
        reader.onerror = rej
        reader.readAsDataURL(file)
      })

      // Extract raw base64 (without the data:image/...;base64, prefix)
      const b64 = dataUrl.split(',')[1]

      setPendingImage(b64)
      setPendingPreview(dataUrl)

      // Store the full data URL (not blob URL) so it persists in localStorage
      onAddMessage('user', '📷 Image uploaded', { image_preview: dataUrl })
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
          <div className="answer-length-pills">
            <span className="length-label">उत्तर / Answer:</span>
            {[
              { key: 'short', label: 'Short', hindi: 'संक्षिप्त', icon: '⚡' },
              { key: 'medium', label: 'Medium', hindi: 'मध्यम', icon: '📝' },
              { key: 'long', label: 'Detailed', hindi: 'विस्तृत', icon: '📖' },
            ].map((opt) => (
              <button
                key={opt.key}
                className={`length-pill ${answerLength === opt.key ? 'active' : ''}`}
                onClick={() => setAnswerLength(opt.key)}
                title={opt.hindi}
              >
                <span className="pill-icon">{opt.icon}</span>
                <span className="pill-label">{opt.label}</span>
              </button>
            ))}
          </div>
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
                    alt="crop photo"
                    className="chat-img-preview"
                  />
                )}
                {m.text}
              </div>
              {m.diagnosis &&
                (m.diagnosis.disease || m.diagnosis.top_disease) &&
                m.diagnosis.disease !== 'Unknown' && (
                  <DiagnosisCard data={m.diagnosis} compact />
                )}
              {m.role === 'assistant' && m.text && (
                <button
                  className={`tts-btn ${speakingId === i ? 'speaking' : ''}`}
                  onClick={(e) => { e.stopPropagation(); handleSpeak(m.text, i) }}
                  title={speakingId === i ? 'Stop speaking' : 'Listen to reply'}
                >
                  {speakingId === i ? '⏹️' : '🔊'}
                </button>
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
        <div className="pending-image-bar">
          <img src={pendingPreview} alt="attached" className="pending-thumb" />
          <span>📷 Image attached — will be sent with your next message</span>
          <button
            className="pending-remove"
            onClick={() => { setPendingImage(null); setPendingPreview(null) }}
            title="Remove"
          >✕</button>
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
        {/* Hidden file inputs */}
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          onChange={handleFileInput}
          hidden
        />
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileInput}
          hidden
        />
        <button type="button" className="chat-action-btn" onClick={openFilePicker} title="Upload from gallery / गैलरी से अपलोड">
          🖼️
        </button>
        <button type="button" className="chat-action-btn" onClick={openCamera} title="Take photo / फ़ोटो लें">
          📸
        </button>
        <button className="chat-send" type="submit" disabled={loading || !input.trim()}>
          ➤
        </button>
      </form>
    </div>
  )
})

export default ChatInterface

