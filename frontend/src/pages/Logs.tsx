import React, { useEffect, useState } from 'react'
import { fetchAuditFiles } from '../api/client'
import AuditTable from '../components/AuditTable'

export default function Logs() {
  const [files, setFiles] = useState<string[]>([])
  const [error, setError] = useState('')

  async function refresh() {
    try {
      const res = await fetchAuditFiles()
      setFiles(res?.audit_files || res?.files || [])
    } catch (e: any) {
      setError(String(e?.message || e))
    }
  }

  useEffect(() => { refresh() }, [])

  return (
    <div>
      <h1>Audit Logs</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <AuditTable files={files} />
    </div>
  )
}
