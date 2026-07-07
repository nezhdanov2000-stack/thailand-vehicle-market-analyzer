/**
 * medianAge.js — Median price by age bucket, grouped bar chart (Cars vs Motorcycles)
 * Derives age buckets client-side from the scatter_data array.
 */

import {
  Chart, BarController, CategoryScale, LinearScale,
  BarElement, Tooltip, Legend,
} from 'chart.js'
Chart.register(BarController, CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const AGE_BUCKETS = [
  { label: '0-2 yrs', min: 0, max: 2 },
  { label: '3-5 yrs', min: 3, max: 5 },
  { label: '6-10 yrs', min: 6, max: 10 },
  { label: '10+ yrs', min: 11, max: 999 },
]

function median(arr) {
  if (!arr.length) return 0
  const sorted = [...arr].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid]
}

export function renderMedianChart(scatterData) {
  const ctx = document.getElementById('median-chart')
  if (!ctx || !scatterData.length) return

  const labels = AGE_BUCKETS.map(b => b.label)

  const carMedians  = AGE_BUCKETS.map(bucket => {
    const prices = scatterData
      .filter(r => r.vehicle_type?.toLowerCase() !== 'motorcycle'
                && r.vehicle_age >= bucket.min && r.vehicle_age <= bucket.max)
      .map(r => r.price / 1000)
    return Math.round(median(prices))
  })

  const motoMedians = AGE_BUCKETS.map(bucket => {
    const prices = scatterData
      .filter(r => r.vehicle_type?.toLowerCase() === 'motorcycle'
                && r.vehicle_age >= bucket.min && r.vehicle_age <= bucket.max)
      .map(r => r.price / 1000)
    return Math.round(median(prices))
  })

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Car',
          data: carMedians,
          backgroundColor: 'rgba(79,142,247,0.75)',
          borderRadius: 6,
          borderSkipped: false,
        },
        {
          label: 'Motorcycle',
          data: motoMedians,
          backgroundColor: 'rgba(247,122,79,0.75)',
          borderRadius: 6,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
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
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ฿${ctx.parsed.y}k`,
          },
        },
      },
      scales: {
        x: {
          grid:  { display: false },
          ticks: { color: '#8B9DC3', font: { size: 10 } },
        },
        y: {
          grid:  { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#4B5A7A', font: { size: 10 }, callback: v => `฿${v}k` },
        },
      },
    },
  })
}
