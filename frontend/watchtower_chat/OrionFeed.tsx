import { useEffect, useState } from "react";

export default function OrionFeed() {
  const [logs, setLogs] = useState<any[]>([]);
  useEffect(() => {
    fetch("/logs/chat/watchtower_room.jsonl")
      .then((r) => r.text())
      .then((t) => {
        const lines = t.trim().split("\n").filter(Boolean);
        const parsed = lines.map((l) => {
          try { return JSON.parse(l); } catch { return null; }
        }).filter(Boolean);
        setLogs(parsed as any[]);
      })
      .catch(() => setLogs([]));
  }, []);
  return (
    <div className="bg-gray-900 text-gray-100 p-4 rounded-xl">
      <h2 className="text-xl font-bold mb-2">🛰 Orion Control Feed</h2>
      <div className="space-y-1 max-h-96 overflow-y-auto">
        {logs.map((e: any, i: number) => (
          <div key={i} className="text-sm">
            <span className="font-semibold">{e.agent}</span>: {e.message || e.content || e.event}
          </div>
        ))}
      </div>
    </div>
  );
}
