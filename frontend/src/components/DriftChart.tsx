import React from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function DriftChart({ data }: { data: { index: number; score: number }[] }) {
  if (!data || data.length === 0) return <p>No drift data.</p>
  return (
    <div style={{ width: 420, height: 240, border: '1px solid #eee', padding: 8 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="index" />
          <YAxis domain={[0, 'dataMax + 0.1']} />
          <Tooltip />
          <Line type="monotone" dataKey="score" stroke="#8884d8" strokeWidth={2} dot={{ r: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
