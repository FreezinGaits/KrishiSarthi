import './VendorList.css'

export default function VendorList({ vendors = [], status = 'idle', matchedDisease = null }) {
  if (status === 'loading') {
    return (
      <div className="vendor-empty">
        <span>⏳</span>
        <p>Loading vendor data...</p>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="vendor-empty">
        <span>❌</span>
        <p>Failed to load vendors. Check if backend is running.</p>
      </div>
    )
  }

  if (!vendors.length) {
    return (
      <div className="vendor-empty">
        <span>📍</span>
        <p>{matchedDisease
          ? 'No vendors found with matching pesticides for this disease.'
          : 'No vendors found nearby. Try sharing your location.'
        }</p>
      </div>
    )
  }

  return (
    <div className="vendor-list">
      {vendors.map((v, i) => (
        <div className={`vendor-card ${v.match_score ? 'matched' : ''}`} key={i}>
          <div className="vendor-top">
            <h4 className="vendor-name">{v.name}</h4>
            <div className="vendor-badges">
              {v.match_score && (
                <span className="vendor-match-badge">✅ {v.match_score} match{v.match_score > 1 ? 'es' : ''}</span>
              )}
              {v.rating && (
                <span className="vendor-rating">
                  ⭐ {typeof v.rating === 'number' ? v.rating.toFixed(1) : v.rating}
                </span>
              )}
            </div>
          </div>
          <p className="vendor-address">{v.address}{v.city ? `, ${v.city}` : ''}</p>
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
              <span className="products-label">{matchedDisease ? '💊 Available treatments:' : '📦 Products:'}</span>
              <div className="product-tags">
                {v.products.map((p, j) => (
                  <span key={j} className={`product-tag ${matchedDisease ? 'matched-product' : ''}`}>{p}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
