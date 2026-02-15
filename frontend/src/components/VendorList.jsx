import './VendorList.css'

export default function VendorList({ vendors = [] }) {
  if (!vendors.length) {
    return (
      <div className="vendor-empty">
        <span>📍</span>
        <p>Loading vendor data...</p>
      </div>
    )
  }

  return (
    <div className="vendor-list">
      {vendors.map((v, i) => (
        <div className="vendor-card" key={i}>
          <div className="vendor-top">
            <h4 className="vendor-name">{v.name}</h4>
            {v.rating && (
              <span className="vendor-rating">
                ⭐ {typeof v.rating === 'number' ? v.rating.toFixed(1) : v.rating}
              </span>
            )}
          </div>
          <p className="vendor-address">{v.address}</p>
          <div className="vendor-meta">
            {v.distance_km != null && (
              <span className="vendor-distance">📏 {v.distance_km.toFixed(1)} km</span>
            )}
            {v.phone && (
              <a className="vendor-phone" href={`tel:${v.phone}`}>📞 {v.phone}</a>
            )}
          </div>
          {v.products && v.products.length > 0 && (
            <div className="vendor-products">
              {v.products.slice(0, 4).map((p, j) => (
                <span key={j} className="product-tag">{p}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
