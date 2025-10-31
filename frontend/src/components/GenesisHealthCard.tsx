import React, { useEffect, useState } from 'react'
import { api } from '../api/client'

interface HealthRow {
  timestamp: string
  port: string
  status: string
  mode: string
}

export default function GenesisHealthCard() {
  const [rows, setRows] = useState<HealthRow[]>([])
  const [err, setErr] = useState<string>('')

  async function load() {
    try {
      const { data } = await api.get('/health/genesis')
      if (data?.ok && Array.isArray(data.data)) setRows(data.data)
      setErr('')
    } catch (e: any) {
      setErr(String(e?.message || e))
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [])

  const latest = rows.length ? rows[rows.length - 1] : undefined
  const status = latest?.status || 'n/a'
  const color = status === 'ok' ? '#34d399' : status === 'restart' ? '#f59e0b' : status === 'fail' ? '#f87171' : '#9ca3af'

  return (
    <div style={{ padding: 16, borderRadius: 12, background: '#0f172a', color: '#e5e7eb', minWidth: 300 }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Genesis Health</h2>
      {latest ? (
        <div>
          <p> Status: <span style={{ color }}>{status}</span></p>
          <p> Port: {latest.port || '—'}</p>
          <p> Mode: {latest.mode || '—'}</p>
          <p> Updated: {latest.timestamp || '—'}</p>
        </div>
      ) : (
        <p>No data yet.</p>
      )}
      {err && <p style={{ color: '#f87171', marginTop: 8 }}>Error: {err}</p>}
    </div>
  )
}
