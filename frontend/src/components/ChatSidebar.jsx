import { useState } from 'react'
import './ChatSidebar.css'

function getTimeAgo(iso) {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
  return new Date(iso).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
}

export default function ChatSidebar({
  sessions,
  activeId,
  onCreateSession,
  onSwitchSession,
  onDeleteSession,
  onRenameSession,
}) {
  const [renamingId, setRenamingId] = useState(null)
  const [renameValue, setRenameValue] = useState('')

  function startRename(e, session) {
    e.stopPropagation()
    setRenamingId(session.id)
    setRenameValue(session.title)
  }

  function finishRename() {
    if (renamingId && renameValue.trim()) {
      onRenameSession(renamingId, renameValue.trim())
    }
    setRenamingId(null)
    setRenameValue('')
  }

  function handleDelete(e, id) {
    e.stopPropagation()
    onDeleteSession(id)
  }

  return (
    <aside className="chat-sidebar">
      <div className="sidebar-header">
        <h3 className="sidebar-title">💬 Chats</h3>
        <button className="sidebar-new-btn" onClick={onCreateSession} title="New Chat">
          ➕
        </button>
      </div>

      <div className="sidebar-sessions">
        {sessions.map((s) => {
          const isActive = s.id === activeId
          const lastMsg = s.messages.length > 0
            ? s.messages[s.messages.length - 1].text || ''
            : ''
          const preview = lastMsg.slice(0, 45) + (lastMsg.length > 45 ? '…' : '')
          const msgCount = s.messages.filter((m) => m.role === 'user').length

          return (
            <div
              key={s.id}
              className={`sidebar-session ${isActive ? 'active' : ''}`}
              onClick={() => onSwitchSession(s.id)}
            >
              <div className="session-main">
                <div className="session-top-row">
                  {renamingId === s.id ? (
                    <input
                      className="session-rename-input"
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onBlur={finishRename}
                      onKeyDown={(e) => e.key === 'Enter' && finishRename()}
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <span className="session-name">{s.title}</span>
                  )}
                  <span className="session-time">{getTimeAgo(s.createdAt)}</span>
                </div>
                <div className="session-preview">{preview || 'No messages yet'}</div>
                {msgCount > 0 && (
                  <div className="session-meta">{msgCount} message{msgCount !== 1 ? 's' : ''}</div>
                )}
              </div>

              <div className="session-actions">
                <button
                  className="session-action rename"
                  onClick={(e) => startRename(e, s)}
                  title="Rename"
                >
                  ✏️
                </button>
                <button
                  className="session-action delete"
                  onClick={(e) => handleDelete(e, s.id)}
                  title="Delete"
                >
                  🗑️
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
