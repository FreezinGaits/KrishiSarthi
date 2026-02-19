import { useState, useCallback, useRef, useEffect } from 'react'

const STORAGE_SESSIONS = 'krishi_sessions'
const STORAGE_ACTIVE = 'krishi_active_session'

const DEFAULT_WELCOME = {
  role: 'assistant',
  text: 'नमस्ते! मैं कृषि-सारथी हूँ 🌾\nमैं आपकी फसल की बीमारी पहचानने, इलाज बताने और नज़दीकी दुकान खोजने में मदद कर सकता हूँ।\n\nHow can I help you today?',
}

function loadSessions() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_SESSIONS)) || []
  } catch {
    return []
  }
}

function saveSessions(sessions) {
  localStorage.setItem(STORAGE_SESSIONS, JSON.stringify(sessions))
}

function saveActiveId(id) {
  localStorage.setItem(STORAGE_ACTIVE, id)
}

function makeSession(index) {
  return {
    id: `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    title: `Chat ${index}`,
    createdAt: new Date().toISOString(),
    messages: [DEFAULT_WELCOME],
  }
}

/**
 * Custom hook for multi-chat session management.
 *
 * Returns:
 *   sessions        — array of all sessions
 *   activeSession   — the currently active session object
 *   activeId        — id of the active session
 *   createSession() — create and switch to a new session
 *   switchSession(id)
 *   deleteSession(id)
 *   renameSession(id, title)
 *   addMessage(role, text, extra)  — add message to active session
 *   setActiveMessages(msgs)        — replace messages for active session
 */
export default function useChatSessions() {
  const [sessions, setSessions] = useState(() => {
    const loaded = loadSessions()
    if (loaded.length === 0) {
      const first = makeSession(1)
      saveSessions([first])
      saveActiveId(first.id)
      return [first]
    }
    return loaded
  })

  const [activeId, setActiveId] = useState(() => {
    const stored = localStorage.getItem(STORAGE_ACTIVE)
    const loaded = loadSessions()
    if (stored && loaded.find((s) => s.id === stored)) return stored
    return loaded[0]?.id || ''
  })

  // Persist whenever sessions or activeId change
  const isInitialMount = useRef(true)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }
    saveSessions(sessions)
  }, [sessions])

  useEffect(() => {
    if (activeId) saveActiveId(activeId)
  }, [activeId])

  const activeSession = sessions.find((s) => s.id === activeId) || sessions[0]

  // ── CRUD ──────────────────────────────────────

  const createSession = useCallback(() => {
    setSessions((prev) => {
      const next = makeSession(prev.length + 1)
      setActiveId(next.id)
      return [next, ...prev]
    })
  }, [])

  const switchSession = useCallback((id) => {
    setActiveId(id)
  }, [])

  const deleteSession = useCallback(
    (id) => {
      setSessions((prev) => {
        const filtered = prev.filter((s) => s.id !== id)
        if (filtered.length === 0) {
          const fresh = makeSession(1)
          setActiveId(fresh.id)
          return [fresh]
        }
        if (activeId === id) {
          setActiveId(filtered[0].id)
        }
        return filtered
      })
      // Fire-and-forget backend cleanup
      fetch(`/api/sessions/${id}`, { method: 'DELETE' }).catch(() => {})
    },
    [activeId]
  )

  const renameSession = useCallback((id, newTitle) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title: newTitle.trim() || s.title } : s))
    )
  }, [])

  // ── Messages ──────────────────────────────────

  const addMessage = useCallback(
    (role, text, extra = {}) => {
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== activeId) return s
          const updated = { ...s, messages: [...s.messages, { role, text, ...extra }] }

          // Auto-title: use first user message
          const userMsgs = updated.messages.filter((m) => m.role === 'user')
          if (userMsgs.length === 1 && role === 'user') {
            updated.title = text.slice(0, 30) + (text.length > 30 ? '…' : '')
          }

          return updated
        })
      )
    },
    [activeId]
  )

  const setActiveMessages = useCallback(
    (msgs) => {
      setSessions((prev) =>
        prev.map((s) => (s.id === activeId ? { ...s, messages: msgs } : s))
      )
    },
    [activeId]
  )

  return {
    sessions,
    activeSession,
    activeId,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
    addMessage,
    setActiveMessages,
  }
}
