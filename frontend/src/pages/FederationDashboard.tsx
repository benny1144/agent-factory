import React, { useEffect, useMemo, useState } from 'react'
import { api, getWsUrl } from '../api/client'

interface FedItem { ts: string; status: string; topic: string; source: string; sha256: string; actor: string; notes: string }

async function fetchByStatus(status?: string): Promise<FedItem[]> {
  const url = status ? `/api/federation/updates?status=${encodeURIComponent(status)}` : '/api/federation/updates'
  const { data } = await api.get(url)
  return data.items || []
}

export default function FederationDashboard() {
  const [pending, setPending] = useState<FedItem[]>([])
  const [approved, setApproved] = useState<FedItem[]>([])
  const [published, setPublished] = useState<FedItem[]>([])
  const [rejected, setRejected] = useState<FedItem[]>([])
  const [lastEvent, setLastEvent] = useState<any>(null)

  const refresh = async () => {
    const [p1, p2, p3, p4] = await Promise.all([
      fetchByStatus('pending').catch(() => []),
      fetchByStatus('approved').catch(() => []),
      fetchByStatus('published').catch(() => []),
      fetchByStatus('rejected').catch(() => []),
    ])
    setPending(p1); setApproved(p2); setPublished(p3); setRejected(p4)
  }

  useEffect(() => {
    refresh()
    // connect websocket for live federation events
    let ws: WebSocket | null = null
    try {
      const wsUrl = getWsUrl().replace(/\/ws$/, '/api/ws/telemetry') // ensure telemetry endpoint
      ws = new WebSocket(wsUrl)
      ws.onopen = () => {
        // console.log('WS connected (federation dashboard)')
      }
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data)
          if (msg?.category === 'federation') {
            setLastEvent(msg)
            refresh()
          }
        } catch {}
      }
      ws.onerror = () => {}
    } catch {}
    return () => { try { ws?.close() } catch {} }
  }, [])

  const Panel = ({ title, count, color }: { title: string; count: number; color: string }) => (
    <div style={{ flex: 1, border: '1px solid #eee', borderRadius: 8, padding: 12 }}>
      <div style={{ fontSize: 12, color: '#666' }}>{title}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{count}</div>
    </div>
  )

  return (
    <div>
      <h1>Federation Insights</h1>
      <p style={{ color: '#666' }}>Live view of pending, approved, and published federation updates.</p>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Panel title="Pending" count={pending.length} color="#a36" />
        <Panel title="Approved" count={approved.length} color="#0a7" />
        <Panel title="Published" count={published.length} color="#06a" />
        <Panel title="Rejected" count={rejected.length} color="#999" />
      </div>
      {lastEvent && (
        <div style={{ fontSize: 12, background: '#fafafa', border: '1px solid #eee', padding: 8, borderRadius: 6 }}>
          <b>Last event:</b> {lastEvent.event} — {lastEvent?.data?.topic}
        </div>
      )}
      <div style={{ marginTop: 16 }}>
        <h3>Recent Published</h3>
        <ul>
          {published.slice(-10).reverse().map((it, idx) => (
            <li key={idx}>
              <code>{it.ts}</code> — <b>{it.topic}</b> by {it.actor} ({it.source})
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
