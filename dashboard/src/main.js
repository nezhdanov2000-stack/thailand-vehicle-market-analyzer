/**
 * main.js — Dashboard orchestrator
 * Loads market_stats.json + CSVs, renders all charts and the deals table.
 */

import Papa from 'papaparse'
import { renderScatterChart }     from './charts/priceAge.js'
import { renderDepreciationChart } from './charts/depreciation.js'
import { renderProvinceChart }     from './charts/province.js'
import { renderMedianChart }       from './charts/medianAge.js'
import { renderKpiCards }          from './components/kpiCards.js'
import { renderDealsTable }        from './components/dealsTable.js'

// ── Data loading helpers ──────────────────────────────────────────

async function loadJSON(path) {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`)
  return res.json()
}

async function loadCSV(path) {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`)
  const text = await res.text()
  return new Promise((resolve, reject) => {
    Papa.parse(text, {
      header: true,
      skipEmptyLines: true,
      dynamicTyping: true,
      complete: (results) => resolve(results.data),
      error: reject,
    })
  })
}

// ── Boot ──────────────────────────────────────────────────────────

async function boot() {
  const overlay = document.getElementById('loading-overlay')
  const lastUpdated = document.getElementById('last-updated')

  try {
    // Load all data in parallel
    const [stats, deals] = await Promise.all([
      loadJSON('/data/market_stats.json'),
      loadCSV('/data/top_deals.csv').catch(() => []),
    ])

    // Timestamp
    const now = new Date()
    lastUpdated.textContent = `Updated ${now.toLocaleTimeString('en-GB')}`

    // ── KPI Cards ──────────────────────────────────────────────
    renderKpiCards(stats)

    // ── Charts ────────────────────────────────────────────────
    // 1. Scatter: price vs age (uses scatter_data from stats JSON)
    renderScatterChart(stats.scatter_data || [], deals)

    // 2. Depreciation curves (uses depreciation_data from stats JSON)
    renderDepreciationChart(stats.depreciation_data || [])

    // 3. Province bar chart
    renderProvinceChart(stats.province_data || [])

    // 4. Median price by age bucket (derive from scatter_data)
    renderMedianChart(stats.scatter_data || [])

    // ── Deals Table ────────────────────────────────────────────
    renderDealsTable(deals)

    // ── Hide loading overlay ───────────────────────────────────
    overlay.classList.add('hidden')
    setTimeout(() => overlay.remove(), 600)

    // Animate sections in
    document.querySelectorAll('.card, .kpi-card').forEach((el, i) => {
      el.style.animationDelay = `${i * 40}ms`
      el.classList.add('fade-in')
    })

  } catch (err) {
    console.error('Dashboard load error:', err)
    overlay.innerHTML = `
      <div style="text-align:center;padding:2rem;max-width:480px">
        <div style="font-size:3rem;margin-bottom:1rem">⚠️</div>
        <div style="font-size:1.1rem;font-weight:700;margin-bottom:0.75rem;color:#F0F4FF">
          No data found
        </div>
        <div style="font-size:0.85rem;color:#8B9DC3;line-height:1.7">
          Run the Python pipeline first to generate market data:<br>
          <code style="background:rgba(255,255,255,0.08);padding:0.4rem 0.8rem;
            border-radius:6px;font-family:monospace;font-size:0.8rem;display:inline-block;margin-top:0.5rem">
            python main.py --mock
          </code>
        </div>
      </div>
    `
  }
}

boot()
