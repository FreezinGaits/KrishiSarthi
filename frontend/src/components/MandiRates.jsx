import { useState, useEffect, useMemo } from 'react'
import './MandiRates.css'

const API_BASE = '/api'

export default function MandiRates() {
  const [data, setData] = useState([])
  const [filters, setFilters] = useState({ states: [], districts: [], varieties: [] })
  const [state, setState] = useState('')
  const [district, setDistrict] = useState('')
  const [variety, setVariety] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState('modal_price')
  const [sortDir, setSortDir] = useState('desc')

  useEffect(() => { fetchData() }, [state, district, variety])

  async function fetchData() {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (state) params.set('state', state)
      if (district) params.set('district', district)
      if (variety) params.set('variety', variety)
      const resp = await fetch(`${API_BASE}/mandi-rates?${params}`)
      const json = await resp.json()
      setData(json.data || [])
      setFilters(json.filters || { states: [], districts: [], varieties: [] })
    } catch (err) {
      console.error('Mandi fetch error:', err)
    } finally {
      setLoading(false)
    }
  }

  // Client-side search + sort
  const processed = useMemo(() => {
    let rows = data
    if (search) {
      const q = search.toLowerCase()
      rows = rows.filter(
        (r) =>
          r.market.toLowerCase().includes(q) ||
          r.variety.toLowerCase().includes(q) ||
          r.district.toLowerCase().includes(q)
      )
    }
    rows = [...rows].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey]
      if (typeof av === 'number') return sortDir === 'asc' ? av - bv : bv - av
      return sortDir === 'asc' ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av))
    })
    return rows
  }, [data, search, sortKey, sortDir])

  // Summary stats
  const stats = useMemo(() => {
    if (processed.length === 0) return null
    const prices = processed.map((d) => d.modal_price)
    return {
      count: processed.length,
      avgPrice: Math.round(prices.reduce((a, b) => a + b, 0) / prices.length),
      maxPrice: Math.max(...prices),
      minPrice: Math.min(...prices),
    }
  }, [processed])

  const priceRange = stats ? stats.maxPrice - stats.minPrice : 1

  function handleSort(key) {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  function SortIcon({ col }) {
    if (sortKey !== col) return <span className="sort-icon dim">⇅</span>
    return <span className="sort-icon">{sortDir === 'asc' ? '↑' : '↓'}</span>
  }

  function priceClass(price) {
    if (!stats || priceRange === 0) return ''
    const pct = (price - stats.minPrice) / priceRange
    if (pct >= 0.7) return 'price-high'
    if (pct <= 0.3) return 'price-low'
    return 'price-mid'
  }

  function clearFilters() {
    setState('')
    setDistrict('')
    setVariety('')
    setSearch('')
  }

  const hasFilters = state || district || variety || search

  return (
    <div className="mandi-container">
      {/* ── Header ── */}
      <div className="mandi-header">
        <div>
          <h2 className="mandi-title">🏪 Mandi Marketplace</h2>
          <p className="mandi-subtitle">Latest crop prices from mandis across India</p>
        </div>
        {hasFilters && (
          <button className="mandi-clear-btn" onClick={clearFilters}>
            ✕ Clear Filters
          </button>
        )}
      </div>

      {/* ── Filters ── */}
      <div className="mandi-filters">
        <div className="filter-group">
          <label className="filter-label">🌍 State</label>
          <select
            className="filter-select"
            value={state}
            onChange={(e) => { setState(e.target.value); setDistrict('') }}
          >
            <option value="">All States</option>
            {filters.states.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-label">📍 District</label>
          <select
            className="filter-select"
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
          >
            <option value="">All Districts</option>
            {filters.districts.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-label">🌾 Commodity</label>
          <select
            className="filter-select"
            value={variety}
            onChange={(e) => setVariety(e.target.value)}
          >
            <option value="">All Commodities</option>
            {filters.varieties.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </div>

        <div className="filter-group search-group">
          <label className="filter-label">🔍 Search</label>
          <input
            className="filter-input"
            type="text"
            placeholder="Market, commodity, district..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* ── Summary Cards ── */}
      {stats && (
        <div className="mandi-stats">
          <div className="stat-card">
            <span className="stat-value">{stats.count}</span>
            <span className="stat-label">Markets</span>
          </div>
          <div className="stat-card avg">
            <span className="stat-value">₹{stats.avgPrice.toLocaleString('en-IN')}</span>
            <span className="stat-label">Avg Price / Qtl</span>
          </div>
          <div className="stat-card high">
            <span className="stat-value">₹{stats.maxPrice.toLocaleString('en-IN')}</span>
            <span className="stat-label">Highest</span>
          </div>
          <div className="stat-card low">
            <span className="stat-value">₹{stats.minPrice.toLocaleString('en-IN')}</span>
            <span className="stat-label">Lowest</span>
          </div>
        </div>
      )}

      {/* ── Table ── */}
      {loading ? (
        <div className="mandi-loading">
          <div className="mandi-spinner" />
          <p>Loading mandi rates…</p>
        </div>
      ) : processed.length === 0 ? (
        <div className="mandi-empty">
          <span className="empty-icon">📦</span>
          <p>No mandi data found for the selected filters.</p>
          {hasFilters && (
            <button className="mandi-clear-btn" onClick={clearFilters}>Clear Filters</button>
          )}
        </div>
      ) : (
        <div className="mandi-table-wrap">
          <table className="mandi-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('market')}>
                  Market <SortIcon col="market" />
                </th>
                <th onClick={() => handleSort('district')}>
                  District <SortIcon col="district" />
                </th>
                <th onClick={() => handleSort('variety')}>
                  Commodity <SortIcon col="variety" />
                </th>
                <th className="th-price" onClick={() => handleSort('min_price')}>
                  Min ₹/Qtl <SortIcon col="min_price" />
                </th>
                <th className="th-price" onClick={() => handleSort('max_price')}>
                  Max ₹/Qtl <SortIcon col="max_price" />
                </th>
                <th className="th-price" onClick={() => handleSort('modal_price')}>
                  Modal ₹/Qtl <SortIcon col="modal_price" />
                </th>
              </tr>
            </thead>
            <tbody>
              {processed.map((row, i) => (
                <tr key={i}>
                  <td className="td-market">
                    <span className="market-name">{row.market}</span>
                    <span className="market-state">{row.state}</span>
                  </td>
                  <td>{row.district}</td>
                  <td>
                    <span className="variety-badge">{row.variety}</span>
                  </td>
                  <td className={`td-price ${priceClass(row.min_price)}`}>
                    ₹{row.min_price.toLocaleString('en-IN')}
                  </td>
                  <td className={`td-price ${priceClass(row.max_price)}`}>
                    ₹{row.max_price.toLocaleString('en-IN')}
                  </td>
                  <td className={`td-price td-modal ${priceClass(row.modal_price)}`}>
                    ₹{row.modal_price.toLocaleString('en-IN')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
