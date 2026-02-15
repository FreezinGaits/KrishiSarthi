import { useEffect, useRef } from 'react'
import './MapView.css'

export default function MapView({ vendors = [], center }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)

  useEffect(() => {
    if (!mapRef.current || typeof window === 'undefined') return
    if (mapInstanceRef.current) return // Already initialized

    const L = window.L
    if (!L) return

    const lat = center?.lat || 30.9
    const lng = center?.lng || 75.85

    const map = L.map(mapRef.current).setView([lat, lng], 12)
    mapInstanceRef.current = map

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)

    // User marker
    L.marker([lat, lng], {
      icon: L.divIcon({
        className: 'user-marker',
        html: '<div class="user-pin">📍</div>',
        iconSize: [30, 30],
        iconAnchor: [15, 30],
      }),
    })
      .addTo(map)
      .bindPopup('आपकी लोकेशन')

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [center])

  useEffect(() => {
    const map = mapInstanceRef.current
    const L = window.L
    if (!map || !L) return

    vendors.forEach((v) => {
      if (!v.lat || !v.lng) return
      L.marker([v.lat, v.lng], {
        icon: L.divIcon({
          className: 'vendor-marker',
          html: '<div class="vendor-pin">🏪</div>',
          iconSize: [30, 30],
          iconAnchor: [15, 30],
        }),
      })
        .addTo(map)
        .bindPopup(`
          <strong>${v.name}</strong><br/>
          ${v.address || ''}<br/>
          ${v.phone ? `📞 ${v.phone}` : ''}
          ${v.rating ? `<br/>⭐ ${v.rating}` : ''}
        `)
    })
  }, [vendors])

  return <div ref={mapRef} className="map-container" />
}
