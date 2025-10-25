import React, { useState } from 'react'
import { sendJunieTask, queryGPT } from '../api/client'

export default function JunieConsole() {
  const [text, setText] = useState('')
  const [resp, setResp] = useState<any>(null)
  const [gptQuery, setGptQuery] = useState('')
  const [gptResp, setGptResp] = useState<any>(null)
  const [error, setError] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const payload = { text }
      const res = await sendJunieTask(payload)
      setResp(res)
    } catch (e: any) {
      setError(String(e?.message || e))
    }
  }

  async function submitGPT(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const res = await queryGPT(gptQuery)
      setGptResp(res)
    } catch (e: any) {
      setError(String(e?.message || e))
    }
  }

  return (
    <div>
      <h1>Junie Console</h1>
      <p>Send a [JUNIE TASK] payload to the local/int Cloudflare Junie Bridge via /api/junie.</p>
      <form onSubmit={submit} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input value={text} onChange={e => setText(e.target.value)} placeholder="Enter [JUNIE TASK] text" style={{ width: 480 }} />
        <button type="submit">Send</button>
      </form>

      <h2 style={{ marginTop: 24 }}>Governance Assistant (GPT)</h2>
      <form onSubmit={submitGPT} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input value={gptQuery} onChange={e => setGptQuery(e.target.value)} placeholder="Ask GPT-5 (stubbed)" style={{ width: 480 }} />
        <button type="submit">Query</button>
      </form>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {resp && (
        <pre style={{ background: '#f7f7f7', padding: 12, marginTop: 12 }}>
{JSON.stringify(resp, null, 2)}
        </pre>
      )}
      {gptResp && (
        <pre style={{ background: '#f0f9ff', padding: 12, marginTop: 12 }}>
:{JSON.stringify(gptResp, null, 2)}
        </pre>
      )}
    </div>
  )
}
