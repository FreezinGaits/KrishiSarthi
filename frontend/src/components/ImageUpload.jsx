import { useState, useRef } from 'react'
import { diagnoseImage } from '../services/api'
import DiagnosisCard from './DiagnosisCard'
import './ImageUpload.css'

export default function ImageUpload({ onDiagnosis }) {
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const fileRef = useRef()
  const cameraRef = useRef()

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setResult(null)
    setPreview(URL.createObjectURL(file))
    uploadFile(file)
  }

  function handleDrop(e) {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (!file || !file.type.startsWith('image/')) return
    setError('')
    setResult(null)
    setPreview(URL.createObjectURL(file))
    uploadFile(file)
  }

  async function uploadFile(file) {
    setLoading(true)
    try {
      const res = await diagnoseImage(file)
      setResult(res)
      if (onDiagnosis) onDiagnosis(res, { from: 'image' })
    } catch {
      setError('Diagnosis failed. कृपया दोबारा कोशिश करें।')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="image-upload">
      <div
        className={`drop-zone ${preview ? 'has-preview' : ''}`}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {preview ? (
          <img src={preview} alt="Crop preview" className="upload-preview" />
        ) : (
          <div className="drop-placeholder">
            <span className="drop-icon">📸</span>
            <p>फसल की फोटो यहाँ drag करें या क्लिक करें</p>
            <p className="drop-hint">Tap to upload crop image</p>
          </div>
        )}
        {loading && (
          <div className="upload-overlay">
            <div className="scan-animation">
              <div className="scan-line" />
            </div>
            <p>🔬 AI analyzing...</p>
          </div>
        )}
      </div>

      {/* ── Action buttons: Camera + Gallery ── */}
      <div className="upload-actions">
        <button
          type="button"
          className="upload-action-btn camera-btn"
          onClick={() => cameraRef.current?.click()}
        >
          📸 <span>Camera / कैमरा</span>
        </button>
        <button
          type="button"
          className="upload-action-btn gallery-btn"
          onClick={() => fileRef.current?.click()}
        >
          🖼️ <span>Gallery / गैलरी</span>
        </button>
      </div>

      {/* Hidden file inputs */}
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        onChange={handleFile}
        hidden
      />
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFile}
        hidden
      />

      {error && <div className="upload-error">⚠️ {error}</div>}
      {result && <DiagnosisCard data={result} />}
    </div>
  )
}

