import { useState, useRef } from 'react'
import { speechToText } from '../services/api'
import './VoiceRecorder.css'

export default function VoiceRecorder({ onTranscript }) {
  const [recording, setRecording] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')
  const mediaRef = useRef(null)
  const chunksRef = useRef([])

  async function startRecording() {
    setError('')
    setTranscript('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        await processAudio(blob)
      }

      recorder.start()
      setRecording(true)
    } catch (e) {
      setError('Microphone access denied. कृपया माइक्रोफ़ोन की अनुमति दें।')
    }
  }

  function stopRecording() {
    mediaRef.current?.stop()
    setRecording(false)
  }

  async function processAudio(blob) {
    setProcessing(true)
    try {
      const res = await speechToText(blob)
      const text = res.transcript || res.text || ''
      setTranscript(text)
      if (text && onTranscript) onTranscript(text)
    } catch {
      setError('Speech recognition failed. कृपया दोबारा कोशिश करें।')
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
