import { useState, useEffect, useRef, useCallback } from 'react'
import { startConversation, sendMarketMessage, getConversationMessages } from '../services/api'
import './VendorChat.css'

const DEMO_FARMER_ID = 'demo-farmer-001'

export default function VendorChat({ vendor, onClose }) {
  const [conversationId, setConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)
  const pollRef = useRef(null)
  const inputRef = useRef(null)

  const vendorId = vendor?.id || `vendor_${vendor?.name?.replace(/\s/g, '_')}`
  const vendorName = vendor?.name || 'Vendor'

  // scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  // Start conversation on mount
  useEffect(() => {
    let cancelled = false
    async function init() {
      try {
        const res = await startConversation(DEMO_FARMER_ID, vendorId)
        if (!cancelled) {
          setConversationId(res.conversation_id)
          setLoading(false)
          inputRef.current?.focus()
        }
      } catch (err) {
        if (!cancelled) {
          setError('Could not connect. कनेक्शन विफल।')
          setLoading(false)
        }
      }
    }
    init()
    return () => { cancelled = true }
  }, [vendorId])

  // Poll for new messages
  useEffect(() => {
    if (!conversationId) return

    async function poll() {
      try {
        const data = await getConversationMessages(conversationId)
        if (data.messages) {
          setMessages(data.messages)
          scrollToBottom()
        }
      } catch (_) {/* silent */}
    }

    poll() // initial fetch
    pollRef.current = setInterval(poll, 3000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [conversationId, scrollToBottom])

  async function handleSend() {
    const text = input.trim()
    if (!text || !conversationId) return

    setInput('')
    setSending(true)

    // Optimistic update
    const optimistic = {
      id: Date.now(),
      conversation_id: conversationId,
      sender_id: DEMO_FARMER_ID,
      message: text,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, optimistic])
    scrollToBottom()

    try {
      await sendMarketMessage(conversationId, DEMO_FARMER_ID, text)
    } catch (err) {
      console.error('Send failed:', err)
    } finally {
      setSending(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="vchat-overlay" onClick={onClose}>
      <div className="vchat-modal" onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="vchat-header">
          <div className="vchat-header-info">
            <span className="vchat-avatar">🏪</span>
            <div>
              <h3>💬 {vendorName}</h3>
              <span className="vchat-status">
                {loading ? 'Connecting…' : 'Online'}
              </span>
            </div>
          </div>
          <button className="vchat-close" onClick={onClose}>&times;</button>
        </div>

        {/* Messages */}
        <div className="vchat-messages">
          {loading && (
            <div className="vchat-system-msg">
              <span className="vchat-loader">⏳</span>
              Starting conversation…<br />
              <span className="vchat-hint">कनेक्ट हो रहा है…</span>
            </div>
          )}

          {error && (
            <div className="vchat-system-msg vchat-error">
              ❌ {error}
            </div>
          )}

          {!loading && !error && messages.length === 0 && (
            <div className="vchat-system-msg">
              👋 Conversation started with <strong>{vendorName}</strong><br />
              <span className="vchat-hint">दुकानदार से बातचीत शुरू हुई</span>
            </div>
          )}

          {messages.map((m) => {
            const isFarmer = m.sender_id === DEMO_FARMER_ID
            return (
              <div key={m.id} className={`vchat-bubble ${isFarmer ? 'farmer' : 'vendor'}`}>
                <span className="vchat-sender">
                  {isFarmer ? '👨‍🌾 You' : `🏪 ${vendorName}`}
                </span>
                <p>{m.message}</p>
                <span className="vchat-time">
                  {new Date(m.timestamp).toLocaleTimeString('en-IN', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
            )
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="vchat-input-area">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message… / संदेश लिखें…"
            disabled={loading || !!error}
            autoComplete="off"
          />
          <button
            className="vchat-send"
            onClick={handleSend}
            disabled={!input.trim() || loading || sending}
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  )
}
