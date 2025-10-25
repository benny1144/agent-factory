import React from 'react'
import { Link, Route, Routes, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Knowledge from './pages/Knowledge'
import Logs from './pages/Logs'
import JunieConsole from './pages/JunieConsole'

export default function App() {
  return (
    <div style={{ fontFamily: 'Inter, system-ui, Arial, sans-serif', padding: 16 }}>
      <nav style={{ display: 'flex', gap: 12, marginBottom: 16, borderBottom: '1px solid #eee', paddingBottom: 12 }}>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/agents">Agents</Link>
        <Link to="/knowledge">Knowledge</Link>
        <Link to="/logs">Logs</Link>
        <Link to="/junie">Junie</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/knowledge" element={<Knowledge />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/junie" element={<JunieConsole />} />
      </Routes>
    </div>
  )
}
