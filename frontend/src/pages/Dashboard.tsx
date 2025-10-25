import React, { useEffect, useState } from 'react'
import { fetchDrift, fetchOptimization } from '../api/client'
import DriftChart from '../components/DriftChart'

export default function Dashboard() {
  const [drift, setDrift] = useState<any>({ count: 0, records: [] })
  const [opt, setOpt] = useState<any>({ count: 0, records: [] })
  const [error, setError] = useState<string>('')
  const [events, setEvents] = useState<string[]>([])

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

  useEffect(() => {
    // Open telemetry websocket
    try {
      const base: string = (import.meta as any).env?.VITE_API_BASE || window.location.origin
      const wsUrl = base.replace(/^http/, 'ws').replace(/\/$/, '') + '/api/ws/telemetry'
      const ws = new WebSocket(wsUrl)
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          const text = typeof msg === 'string' ? msg : msg.message || JSON.stringify(msg)
          setEvents(prev => [...prev.slice(-49), text])
        } catch {
          setEvents(prev => [...prev.slice(-49), String(ev.data)])
        }
      }
      ws.onerror = () => setError('WebSocket error')
      return () => ws.close()
    } catch (e: any) {
      setError(String(e?.message || e))
    }
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
        <div>
          <h3>Live Governance Events</h3>
          <div style={{ width: 360, height: 200, overflow: 'auto', border: '1px solid #eee', padding: 8 }}>
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {events.map((e, i) => (
                <li key={i} style={{ fontSize: 12 }}>{e}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
