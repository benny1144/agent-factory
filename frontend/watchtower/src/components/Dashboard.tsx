import React, { useEffect, useMemo, useState } from "react";

// Lightweight parser for JSONL payloads streamed over SSE
function parseJsonlBlock(block: string): any[] {
  const lines = (block || "").split("\n").filter(Boolean);
  const out: any[] = [];
  for (const ln of lines) {
    try { out.push(JSON.parse(ln)); } catch { /* ignore */ }
  }
  return out;
}

function ageColor(ageMs: number): string {
  // <2 min → green, <5 min → yellow, else red
  if (ageMs < 2 * 60 * 1000) return "#16a34a"; // green-600
  if (ageMs < 5 * 60 * 1000) return "#ca8a04"; // yellow-600
  return "#dc2626"; // red-600
}

export default function Dashboard() {
  const [events, setEvents] = useState<any[]>([]);
  const [raw, setRaw] = useState<string>("");

  useEffect(() => {
    const es = new EventSource('/gov/stream');
    es.onmessage = (e) => {
      setRaw(e.data || "");
      const items = parseJsonlBlock(e.data || "");
      setEvents(items);
    };
    return () => es.close();
  }, []);

  const now = Date.now();

  const metrics = useMemo(() => {
    let orionHeartbeats = 0;
    let genesisOptimizations = 0; // build_complete
    let artisanExecs = 0; // task_success
    let archyAlerts = 0; // ethical_drift_alert

    const lastSeen: Record<string, number> = {};

    for (const ev of events) {
      const ts = new Date(ev.ts || ev.time || Date.now()).getTime();
      const agent = String(ev.agent || '').trim();
      const type = String(ev.type || '').trim();
      const status = String(ev.status || '').trim();

      if (agent) {
        lastSeen[agent] = Math.max(lastSeen[agent] || 0, ts);
      }

      if (agent === 'Orion' && type === 'heartbeat' && status === 'ok') orionHeartbeats++;
      if (agent === 'Genesis' && (type === 'build_complete' || type === 'optimize_complete')) genesisOptimizations++;
      if (agent === 'Artisan' && type === 'task_success') artisanExecs++;
      if (agent === 'Archy' && type === 'ethical_drift_alert') archyAlerts++;
    }

    const agents = ['Orion','Artisan','Genesis','Archy','Forgewright','Librarius'];
    const statusLights = agents.map(a => {
      const ts = lastSeen[a] || 0;
      const ageMs = ts ? (now - ts) : Number.POSITIVE_INFINITY;
      const color = ageColor(ageMs);
      const label = ageMs === Infinity ? 'missing' : `${Math.round(ageMs/1000)}s ago`;
      return { agent: a, ageMs, color, label };
    });

    return { orionHeartbeats, genesisOptimizations, artisanExecs, archyAlerts, statusLights };
  }, [events, now]);

  return (
    <div style={{ padding: 8, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace' }}>
      <h3>🛰️ Federation Loop</h3>
      <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
        <Metric label="Orion pings" value={metrics.orionHeartbeats} />
        <Metric label="Genesis optimizations" value={metrics.genesisOptimizations} />
        <Metric label="Artisan executions" value={metrics.artisanExecs} />
        <Metric label="Archy alerts" value={metrics.archyAlerts} />
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
        {metrics.statusLights.map(s => (
          <div key={s.agent} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: 999, background: s.color, display: 'inline-block' }} />
            <span>{s.agent}: {s.label}</span>
          </div>
        ))}
      </div>
      <details>
        <summary>Raw event bus (tail)</summary>
        <pre style={{ maxHeight: 240, overflow: 'auto', background: '#0b0b0b', color: '#8f8', padding: 8 }}>{raw}</pre>
      </details>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number; }) {
  return (
    <div style={{ background: '#111', color: '#8f8', padding: 12, borderRadius: 6, minWidth: 180 }}>
      <div style={{ fontSize: 12, opacity: 0.8 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700 }}>{value}</div>
    </div>
  );
}
