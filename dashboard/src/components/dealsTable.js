/**
 * dealsTable.js — Sortable, searchable, filterable Top Deals table
 */

let _allDeals   = []
let _sortCol    = 'deal_score'
let _sortAsc    = false
let _search     = ''
let _typeFilter = 'all'

export function renderDealsTable(deals) {
  _allDeals = deals || []
  _rebuildTable()
  _attachListeners()
}

// ── Helpers ───────────────────────────────────────────────────────

function _fmt(n)    { return n != null ? Number(n).toLocaleString() : '—' }
function _fmtK(n)   { return n != null ? `฿${Number(n).toLocaleString()}` : '—' }
function _fmtPct(n) { return n != null ? `${Number(n).toFixed(1)}%` : '—' }
function _fmtKm(n)  { return n != null ? `${Number(n).toLocaleString()} km` : '—' }

function _discountClass(pct) {
  return pct >= 25 ? 'discount-badge--high' : 'discount-badge--medium'
}

function _typeClass(t) {
  return t?.toLowerCase() === 'motorcycle' ? 'type-badge--moto' : 'type-badge--car'
}

function _scoreWidth(score) {
  return Math.round(score * 60)
}

// ── Filter + sort ─────────────────────────────────────────────────

function _filtered() {
  let rows = [..._allDeals]

  if (_typeFilter !== 'all') {
    rows = rows.filter(r => r.vehicle_type?.toLowerCase() === _typeFilter.toLowerCase())
  }

  if (_search.trim()) {
    const q = _search.trim().toLowerCase()
    rows = rows.filter(r =>
      (r.title || '').toLowerCase().includes(q) ||
      (r.make  || '').toLowerCase().includes(q) ||
      (r.model || '').toLowerCase().includes(q) ||
      (r.province || '').toLowerCase().includes(q)
    )
  }

  rows.sort((a, b) => {
    let va = a[_sortCol]
    let vb = b[_sortCol]
    if (typeof va === 'string') va = va.toLowerCase()
    if (typeof vb === 'string') vb = vb.toLowerCase()
    if (va < vb) return _sortAsc ? -1 : 1
    if (va > vb) return _sortAsc ? 1  : -1
    return 0
  })

  return rows
}

// ── Render ────────────────────────────────────────────────────────

function _rebuildTable() {
  const tbody  = document.getElementById('deals-tbody')
  const footer = document.getElementById('deals-footer')
  if (!tbody) return

  const rows = _filtered()

  if (!rows.length) {
    tbody.innerHTML = `
      <tr><td colspan="10">
        <div class="empty-state">
          <div class="empty-state-icon">🔍</div>
          <div class="empty-state-text">No deals match your filters.</div>
        </div>
      </td></tr>
    `
    if (footer) footer.textContent = '0 deals'
    _updateSortHeaders()
    return
  }

  tbody.innerHTML = rows.map((row, i) => {
    const discount    = Number(row.discount_pct) || 0
    const score       = Number(row.deal_score)   || 0
    const vtype       = row.vehicle_type || 'Car'
    const typeClass   = _typeClass(vtype)
    const discClass   = _discountClass(discount)
    const barW        = _scoreWidth(score)

    return `
      <tr>
        <td class="rank-cell">${i + 1}</td>
        <td class="title-cell">
          <div style="font-weight:600;margin-bottom:3px">${row.title || '—'}</div>
          <span class="type-badge ${typeClass}">${vtype}</span>
        </td>
        <td>${row.year || '—'}</td>
        <td class="price-cell">${_fmtK(row.price)}</td>
        <td class="price-cell" style="color:var(--text-secondary)">${_fmtK(row.peer_median)}</td>
        <td>
          <span class="discount-badge ${discClass}">
            ▼ ${_fmtPct(row.discount_pct)}
          </span>
        </td>
        <td class="price-cell" style="color:var(--accent-green)">${_fmtK(row.saving_thb)}</td>
        <td style="color:var(--text-secondary);font-size:0.78rem">${_fmtKm(row.mileage)}</td>
        <td><span class="province-chip">${row.province || '—'}</span></td>
        <td>
          <div class="score-bar-container">
            <div class="score-bar" style="width:${barW}px"></div>
            <span class="score-value">${score.toFixed(3)}</span>
          </div>
        </td>
      </tr>
    `
  }).join('')

  if (footer) {
    footer.textContent = `${rows.length} deal${rows.length !== 1 ? 's' : ''} shown`
  }

  _updateSortHeaders()
}

function _updateSortHeaders() {
  document.querySelectorAll('.deals-table th.sortable').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc')
    if (th.dataset.col === _sortCol) {
      th.classList.add(_sortAsc ? 'sort-asc' : 'sort-desc')
    }
  })
}

// ── Event listeners ───────────────────────────────────────────────

function _attachListeners() {
  // Sort headers
  document.querySelectorAll('.deals-table th.sortable').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col
      if (_sortCol === col) {
        _sortAsc = !_sortAsc
      } else {
        _sortCol = col
        _sortAsc = col === 'rank'
      }
      _rebuildTable()
    })
  })

  // Search
  const searchEl = document.getElementById('deals-search')
  if (searchEl) {
    searchEl.addEventListener('input', e => {
      _search = e.target.value
      _rebuildTable()
    })
  }

  // Type filter
  const filterEl = document.getElementById('type-filter')
  if (filterEl) {
    filterEl.addEventListener('change', e => {
      _typeFilter = e.target.value
      _rebuildTable()
    })
  }
}
