import React, { useEffect, useState } from 'react'
import { fetchDrift, fetchOptimization } from '../api/client'
import DriftChart from '../components/DriftChart'

export default function Dashboard() {
  const [drift, setDrift] = useState<any>({ count: 0, records: [] })
  const [opt, setOpt] = useState<any>({ count: 0, records: [] })
  const [error, setError] = useState<string>('')

  useEffect(() => {
    ;(async () => {
      try {
        const d = await fetchDrift()
        const o = await fetchOptimization()
        setDrift(d)
        setOpt(o)
      } catch (e: any) {
        setError(String(e?.message || e))
      }
    })()
  }, [])

  return (
    <div>
      <h1>Governance Dashboard</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        <div>
          <h3>Ethical Drift (last 10)</h3>
          <DriftChart data={(drift.records || []).map((r: any, i: number) => ({ index: i, score: r?.data?.score ?? 0 }))} />
        </div>
        <div>
          <h3>Optimization Adjustments (last 10)</h3>
          <ul>
            {(opt.records || []).map((r: any, i: number) => (
              <li key={i}>{r?.data?.action} · avg_drift={r?.data?.avg_drift ?? 'n/a'}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
