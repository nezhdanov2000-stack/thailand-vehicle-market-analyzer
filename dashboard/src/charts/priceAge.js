/**
 * priceAge.js — Price vs. Vehicle Age scatter chart
 * Deals are highlighted in amber.
 */

import { Chart, ScatterController, LinearScale, PointElement, Tooltip, Legend } from 'chart.js'
Chart.register(ScatterController, LinearScale, PointElement, Tooltip, Legend)

const COLORS = {
  car:   'rgba(79,142,247,0.55)',
  moto:  'rgba(247,122,79,0.55)',
  deal:  'rgba(251,191,36,0.90)',
}

export function renderScatterChart(scatterData, deals) {
  const ctx = document.getElementById('scatter-chart')
  if (!ctx || !scatterData.length) return

  // Build deal ID set for highlighting
  const dealSet = new Set((deals || []).map(d => `${d.make}_${d.model}_${d.year}_${d.price}`))

  // Separate into categories
  const carPoints  = []
  const motoPoints = []
  const dealPoints = []

  scatterData.forEach(row => {
    const key = `${row.make}_${row.model}_${row.year}_${row.price}`
    const pt  = { x: row.vehicle_age, y: row.price / 1000, label: `${row.make} ${row.model}` }

    if (dealSet.has(key) || (row.discount_pct && row.discount_pct >= 15)) {
      dealPoints.push(pt)
    } else if (row.vehicle_type?.toLowerCase() === 'motorcycle') {
      motoPoints.push(pt)
    } else {
      carPoints.push(pt)
    }
  })

  new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: 'Car',
          data: carPoints,
          backgroundColor: COLORS.car,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
        {
          label: 'Motorcycle',
          data: motoPoints,
          backgroundColor: COLORS.moto,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
        {
          label: 'Deal (≥15% off)',
          data: dealPoints,
          backgroundColor: COLORS.deal,
          pointRadius: 6,
          pointHoverRadius: 8,
          pointStyle: 'star',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },  // legend is in HTML
        tooltip: {
          backgroundColor: 'rgba(14,21,33,0.95)',
          titleColor: '#F0F4FF',
          bodyColor: '#8B9DC3',
          borderColor: 'rgba(79,142,247,0.3)',
          borderWidth: 1,
          callbacks: {
            label: (ctx) => {
              const d = ctx.raw
              return [`${d.label}`, `Age: ${d.x} yrs  ·  ฿${(d.y * 1000).toLocaleString()}`]
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: 'Vehicle Age (years)', color: '#8B9DC3', font: { size: 11 } },
          grid:  { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#4B5A7A', font: { size: 10 } },
        },
        y: {
          title: { display: true, text: 'Price (฿ thousands)', color: '#8B9DC3', font: { size: 11 } },
          grid:  { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#4B5A7A', font: { size: 10 }, callback: v => `฿${v}k` },
        },
      },
    },
  })
}
