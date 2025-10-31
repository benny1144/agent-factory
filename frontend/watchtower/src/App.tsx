import React, { useState } from "react";
import Chatroom from "./components/Chatroom";
import LogStream from "./components/LogStream";
import Dashboard from "./components/Dashboard";

export default function App() {
  const [tab, setTab] = useState<'chat' | 'logs' | 'dashboard'>('dashboard');
  return (
    <div style={{ height: "100vh", display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', gap: 8, padding: 8, background: '#111', color: '#8f8' }}>
        <button onClick={() => setTab('dashboard')}>Federation Loop</button>
        <button onClick={() => setTab('chat')}>Chat</button>
        <button onClick={() => setTab('logs')}>Logs</button>
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        {tab === 'dashboard' && <Dashboard />}
        {tab === 'chat' && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", height: "100%" }}>
            <div>
              <h2 style={{ padding: 8 }}>🜂 Watchtower — Chat</h2>
              <Chatroom />
            </div>
            <div>
              <h2 style={{ padding: 8 }}>📜 Orion Logs</h2>
              <LogStream />
            </div>
          </div>
        )}
        {tab === 'logs' && (
          <div>
            <h2 style={{ padding: 8 }}>📜 Orion Logs (SSE)</h2>
            <LogStream />
          </div>
        )}
      </div>
    </div>
  );
}
