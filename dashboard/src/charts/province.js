/**
 * province.js — Province listing density horizontal bar chart
 */

import {
  Chart, BarController, CategoryScale, LinearScale,
  BarElement, Tooltip, Legend,
} from 'chart.js'
Chart.register(BarController, CategoryScale, LinearScale, BarElement, Tooltip, Legend)

export function renderProvinceChart(provinceData) {
  const ctx = document.getElementById('province-chart')
  if (!ctx || !provinceData.length) return

  const sorted = [...provinceData].sort((a, b) => b.count - a.count).slice(0, 12)
  const labels = sorted.map(p => p.province)
  const counts = sorted.map(p => p.count)
  const medians = sorted.map(p => Math.round(p.median / 1000))

  // Colour gradient based on count
  const maxCount = Math.max(...counts)
  const colors = counts.map(c => {
    const intensity = c / maxCount
    const r = Math.round(79  + (34  - 79)  * (1 - intensity))
    const g = Math.round(142 + (211 - 142) * (1 - intensity))
    const b = Math.round(247 + (153 - 247) * (1 - intensity))
    return `rgba(${r},${g},${b},0.75)`
  })

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Listings',
          data: counts,
          backgroundColor: colors,
          borderRadius: 6,
          borderSkipped: false,
          yAxisID: 'y',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(14,21,33,0.95)',
          titleColor: '#F0F4FF',
          bodyColor: '#8B9DC3',
          borderColor: 'rgba(79,142,247,0.3)',
          borderWidth: 1,
          callbacks: {
            label: (ctx) => {
              const idx = ctx.dataIndex
              return [`Listings: ${counts[idx]}`, `Median price: ฿${medians[idx]}k`]
            },
          },
        },
      },
      scales: {
        x: {
          grid:  { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#4B5A7A', font: { size: 10 } },
        },
        y: {
          grid:  { display: false },
          ticks: { color: '#8B9DC3', font: { size: 10 } },
        },
      },
    },
  })
}
