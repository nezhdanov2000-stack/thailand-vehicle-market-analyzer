/**
 * depreciation.js — Depreciation curve line chart
 * Shows median price vs age for top 6 makes.
 */

import {
  Chart, LineController, LinearScale, CategoryScale,
  PointElement, LineElement, Tooltip, Legend, Filler,
} from 'chart.js'
Chart.register(LineController, LinearScale, CategoryScale, PointElement, LineElement, Tooltip, Legend, Filler)

const PALETTE = [
  '#4F8EF7', '#FBBF24', '#34D399', '#F77A4F',
  '#8B5CF6', '#22D3EE',
]

export function renderDepreciationChart(data) {
  const ctx = document.getElementById('depreciation-chart')
  if (!ctx || !data.length) return

  // Group by make → age → median_price
  const makeMap = {}
  data.forEach(row => {
    if (!makeMap[row.make]) makeMap[row.make] = {}
    makeMap[row.make][row.vehicle_age] = row.median_price
  })

  // Pick top 6 makes by total count proxy (just take first 6 alphabetically if needed)
  const makes = Object.keys(makeMap).sort()
  const topMakes = makes.slice(0, 6)
  const ages = [...new Set(data.map(r => r.vehicle_age))].sort((a, b) => a - b).filter(a => a <= 15)

  const datasets = topMakes.map((make, i) => ({
    label: make,
    data: ages.map(age => (makeMap[make][age] ? makeMap[make][age] / 1000 : null)),
    borderColor: PALETTE[i % PALETTE.length],
    backgroundColor: PALETTE[i % PALETTE.length] + '18',
    fill: false,
    tension: 0.4,
    pointRadius: 3,
    pointHoverRadius: 6,
    borderWidth: 2,
    spanGaps: true,
  }))

  new Chart(ctx, {
    type: 'line',
    data: { labels: ages.map(a => `${a}yr`), datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { color: '#8B9DC3', font: { size: 10 }, boxWidth: 12, padding: 12 },
        },
        tooltip: {
          backgroundColor: 'rgba(14,21,33,0.95)',
          titleColor: '#F0F4FF',
          bodyColor: '#8B9DC3',
          borderColor: 'rgba(79,142,247,0.3)',
          borderWidth: 1,
          callbacks: { label: ctx => `${ctx.dataset.label}: ฿${(ctx.parsed.y * 1000).toLocaleString()}` },
        },
      },
      scales: {
        x: {
          grid:  { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#4B5A7A', font: { size: 10 } },
        },
        y: {
          title: { display: true, text: 'Median Price (฿ thousands)', color: '#8B9DC3', font: { size: 11 } },
          grid:  { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#4B5A7A', font: { size: 10 }, callback: v => `฿${v}k` },
        },
      },
    },
  })
}
