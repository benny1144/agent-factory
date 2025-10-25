import React, { useState } from 'react'
import { uploadKba } from '../api/client'

export default function KBAUploader({ onUploaded }: { onUploaded?: () => void }) {
  const [status, setStatus] = useState('')

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      setStatus('Uploading...')
      const res = await uploadKba(file)
      setStatus('Uploaded: ' + (res?.file || file.name))
      onUploaded && onUploaded()
    } catch (err: any) {
      setStatus('Error: ' + String(err?.message || err))
    }
  }

  return (
    <div>
      <input type="file" onChange={onFileChange} />
      {status && <div style={{ fontSize: 12, marginTop: 6 }}>{status}</div>}
    </div>
  )
}
