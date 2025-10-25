import React, { useEffect, useState } from 'react'
import { fetchKbaIndex } from '../api/client'
import KBAUploader from '../components/KBAUploader'

export default function Knowledge() {
  const [index, setIndex] = useState<any[]>([])
  const [error, setError] = useState('')

  async function refresh() {
    try {
      const res = await fetchKbaIndex()
      setIndex(Array.isArray(res) ? res : [])
    } catch (e: any) {
      setError(String(e?.message || e))
    }
  }

  useEffect(() => { refresh() }, [])

  return (
    <div>
      <h1>Knowledge Base</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <KBAUploader onUploaded={refresh} />
      <h3>Registry Index</h3>
      <table style={{ borderCollapse: 'collapse', width: '100%', maxWidth: 960 }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc', padding: '6px' }}>ID</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc', padding: '6px' }}>Title</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc', padding: '6px' }}>Domain</th>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc', padding: '6px' }}>File</th>
          </tr>
        </thead>
        <tbody>
          {index.map((e: any) => (
            <tr key={e.id}>
              <td style={{ padding: '6px 8px', borderBottom: '1px solid #eee' }}>{e.id}</td>
              <td style={{ padding: '6px 8px', borderBottom: '1px solid #eee' }}>{e.title}</td>
              <td style={{ padding: '6px 8px', borderBottom: '1px solid #eee' }}>{e.domain}</td>
              <td style={{ padding: '6px 8px', borderBottom: '1px solid #eee' }}>{e.file_path}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
