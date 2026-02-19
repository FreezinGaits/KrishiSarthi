import { useState, useRef } from 'react'
import { speechToText, chatWithAgent } from '../services/api'
import './VoiceRecorder.css'
// import { speechToText, chatWithAgent } from '../services/api'

export default function VoiceRecorder({ onTranscript }) {
  const [recording, setRecording] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')
  const mediaRef = useRef(null)
  const chunksRef = useRef([])

  const recognitionRef = useRef(null)
  const transcriptRef = useRef('')

  async function startRecording() {
    setError('')
    setTranscript('')
    transcriptRef.current = ''

    if (!('webkitSpeechRecognition' in window)) {
      setError('Speech recognition not supported in this browser.')
      return
    }

    const recognition = new window.webkitSpeechRecognition()
    recognitionRef.current = recognition

    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-IN'

    recognition.onstart = () => {
      setRecording(true)
    }

    recognition.onresult = (event) => {
      let finalTranscript = ''
      let interimTranscript = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const chunk = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          finalTranscript += chunk
        } else {
          interimTranscript += chunk
        }
      }

      const fullText = finalTranscript + interimTranscript
      transcriptRef.current = fullText
      setTranscript(fullText)
    }

    recognition.onerror = (e) => {
      console.error(e)
      setError('Speech recognition error.')
    }

    recognition.onend = () => {
      setRecording(false)

      const finalText = transcriptRef.current.trim()
      if (!finalText) return

      // Pass transcript to Dashboard → ChatInterface for proper AI processing
      // (ChatInterface has session context, location, and RAG access)
      if (onTranscript) {
        onTranscript(finalText)
      }
    }

    recognition.start()
  }

  function stopRecording() {
    recognitionRef.current?.stop()
  }

  async function processAudio(blob) {
    setProcessing(true)
  
    try {
      // 1️⃣ Convert speech to text
      const sttRes = await speechToText(blob)
      const text = sttRes.transcript || sttRes.text || ''
  
      if (!text) {
        setError('Could not detect speech.')
        return
      }
  
      // 2️⃣ Immediately send to AI chat
      const chatRes = await chatWithAgent(
        text,
        `voice-${Date.now()}`,   // simple session
        null,
        null,
        null,
        'hi',
        {}
      )
  
      // 3️⃣ Show both transcript + AI reply
      setTranscript(text + "\n\n🤖 " + (chatRes.reply || 'No reply received.'))
  
    } catch (err) {
      console.error("VOICE ERROR:", err)
      setError('Voice processing failed. Please try again.')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="voice-recorder">
      <button
        className={`mic-btn ${recording ? 'recording' : ''} ${processing ? 'processing' : ''}`}
        onClick={recording ? stopRecording : startRecording}
        disabled={processing}
      >
        <span className="mic-icon">{processing ? '⏳' : recording ? '⏹' : '🎤'}</span>
        <span className="mic-ripple" />
        <span className="mic-ripple r2" />
        <span className="mic-ripple r3" />
      </button>

      <p className="voice-status">
        {processing ? 'AI सुन रहा है...' : recording ? '🔴 Recording... बोलिए' : 'माइक बटन दबाएं और बोलें'}
      </p>

      {transcript && (
        <div className="transcript-card">
          <div className="transcript-label">📝 Transcript:</div>
          <div className="transcript-text">{transcript}</div>
        </div>
      )}

      {error && <div className="voice-error">⚠️ {error}</div>}
    </div>
  )
}
