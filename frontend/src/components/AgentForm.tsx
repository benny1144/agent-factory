import React, { useState } from 'react'
import { createAgent } from '../api/client'

export default function AgentForm({ onCreated }: { onCreated?: () => void }) {
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [status, setStatus] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    try {
      setStatus('Creating...')
      const res = await createAgent({ name, role })
      setStatus(res?.ok ? 'Created' : 'Error: ' + (res?.error || 'unknown'))
      setName('')
      setRole('')
      onCreated && onCreated()
    } catch (e: any) {
      setStatus('Error: ' + String(e?.message || e))
    }
  }

  return (
    <form onSubmit={submit} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <input value={name} onChange={e => setName(e.target.value)} placeholder="Agent name" required />
      <input value={role} onChange={e => setRole(e.target.value)} placeholder="Role" />
      <button type="submit">Create</button>
      {status && <span style={{ marginLeft: 8, fontSize: 12 }}>{status}</span>}
    </form>
  )
}
