/**
 * kpiCards.js — Renders the KPI cards row from market_stats.json
 */

const KPI_DEFS = [
  {
    key:      'total_listings',
    label:    'Total Listings',
    icon:     '📋',
    format:   v => v.toLocaleString(),
    gradient: 'linear-gradient(135deg,#4F8EF7,#22D3EE)',
    delta:    'Analysed this run',
  },
  {
    key:      'overall_median_price',
    label:    'Market Median',
    icon:     '💰',
    format:   v => `฿${(v / 1000).toFixed(0)}k`,
    gradient: 'linear-gradient(135deg,#FBBF24,#F77A4F)',
    delta:    'All vehicles combined',
  },
  {
    key:      'deal_count',
    label:    'Deals Found',
    icon:     '🎯',
    format:   v => v.toLocaleString(),
    gradient: 'linear-gradient(135deg,#34D399,#059669)',
    delta:    s => `${s.deal_rate_pct}% of market`,
  },
  {
    key:      'avg_discount_pct',
    label:    'Avg Discount',
    icon:     '📉',
    format:   v => `${v}%`,
    gradient: 'linear-gradient(135deg,#8B5CF6,#EC4899)',
    delta:    s => `Max: ${s.max_discount_pct}%`,
  },
  {
    key:      'avg_saving_thb',
    label:    'Avg Saving',
    icon:     '💸',
    format:   v => `฿${(v / 1000).toFixed(0)}k`,
    gradient: 'linear-gradient(135deg,#22D3EE,#4F8EF7)',
    delta:    s => `Best: ฿${(s.max_saving_thb / 1000).toFixed(0)}k`,
  },
  {
    key:      'car_median_price',
    label:    'Car Median',
    icon:     '🚗',
    format:   v => `฿${(v / 1000).toFixed(0)}k`,
    gradient: 'linear-gradient(135deg,#4F8EF7,#8B5CF6)',
    delta:    'Median car price',
  },
]

export function renderKpiCards(stats) {
  const grid = document.getElementById('kpi-grid')
  if (!grid) return

  const cards = KPI_DEFS.map((def, i) => {
    const raw   = stats[def.key] ?? 0
    const value = def.format(raw)
    const delta = typeof def.delta === 'function' ? def.delta(stats) : def.delta

    return `
      <div class="kpi-card fade-in" style="--kpi-gradient:${def.gradient};animation-delay:${i * 60}ms">
        <div class="kpi-icon">${def.icon}</div>
        <div class="kpi-label">${def.label}</div>
        <div class="kpi-value">${value}</div>
        <div class="kpi-delta">${delta}</div>
      </div>
    `
  }).join('')

  grid.innerHTML = cards
}
