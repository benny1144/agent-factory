import React from 'react'

export default function AuditTable({ files }: { files: string[] }) {
  if (!files || files.length === 0) return <p>No [AUDIT] log files found.</p>
  return (
    <table style={{ borderCollapse: 'collapse', width: '100%', maxWidth: 720 }}>
      <thead>
        <tr>
          <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc', padding: '8px' }}>Audit Log Files</th>
        </tr>
      </thead>
      <tbody>
        {files.map((f, i) => (
          <tr key={i}>
            <td style={{ padding: '6px 8px', borderBottom: '1px solid #eee' }}>{f}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
