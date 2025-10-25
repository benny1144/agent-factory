import React, { useEffect, useState } from 'react'
import { fetchAgents } from '../api/client'
import AgentForm from '../components/AgentForm'

export default function Agents() {
  const [agents, setAgents] = useState<any[]>([])
  const [error, setError] = useState('')

  async function refresh() {
    try {
      const res = await fetchAgents()
      setAgents(res?.agents || [])
    } catch (e: any) {
      setError(String(e?.message || e))
    }
  }

  useEffect(() => { refresh() }, [])

  return (
    <div>
      <h1>Agents</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <AgentForm onCreated={refresh} />
      <ul>
        {agents.map(a => (
          <li key={a.id}>{a.name} — <em>{a.role}</em> <small>({a.created_at})</small></li>
        ))}
      </ul>
    </div>
  )
}
