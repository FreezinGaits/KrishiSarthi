import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import { useEffect } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './MapView.css'

// Fix default marker icon issue in Leaflet + bundlers
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const userIcon = L.divIcon({
  className: 'user-marker',
  html: '<div class="user-pin">📍</div>',
  iconSize: [30, 30],
  iconAnchor: [15, 30],
})

const vendorIcon = L.divIcon({
  className: 'vendor-marker',
  html: '<div class="vendor-pin">🏪</div>',
  iconSize: [30, 30],
  iconAnchor: [15, 30],
})

// Auto-fit map bounds to show all markers
function FitBounds({ vendors, center }) {
  const map = useMap()

  useEffect(() => {
    if (vendors.length > 0) {
      const points = vendors
        .filter((v) => v.lat && v.lng)
        .map((v) => [v.lat, v.lng])

      if (center?.lat && center?.lng) {
        points.push([center.lat, center.lng])
      }

      if (points.length > 1) {
        map.fitBounds(points, { padding: [40, 40], maxZoom: 13 })
      }
    }
  }, [vendors, center, map])

  return null
}

export default function MapView({ vendors = [], center }) {
  const lat = center?.lat || 30.9
  const lng = center?.lng || 75.85

  return (
    <MapContainer
      center={[lat, lng]}
      zoom={10}
      className="map-container"
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* User location marker */}
      <Marker position={[lat, lng]} icon={userIcon}>
        <Popup>📍 आपकी लोकेशन</Popup>
      </Marker>

      {/* Vendor markers */}
      {vendors.map((v, i) =>
        v.lat && v.lng ? (
          <Marker key={i} position={[v.lat, v.lng]} icon={vendorIcon}>
            <Popup>
              <strong>{v.name}</strong>
              <br />
              {v.address || ''}
              {v.phone && (
                <>
                  <br />📞 {v.phone}
                </>
              )}
              {v.rating && (
                <>
                  <br />⭐ {v.rating}
                </>
              )}
              {v.distance_km != null && (
                <>
                  <br />📏 {v.distance_km.toFixed(1)} km away
                </>
              )}
            </Popup>
          </Marker>
        ) : null
      )}

      <FitBounds vendors={vendors} center={center} />
    </MapContainer>
  )
}
