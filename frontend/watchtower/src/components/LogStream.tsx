import React, { useEffect, useState } from "react";

export default function LogStream() {
  const [lines, setLines] = useState<string[]>([]);

  useEffect(() => {
    const es = new EventSource('/logs/stream');
    es.onmessage = (e) => {
      const payload = (e.data || '').toString();
      const parts = payload.split('\n').filter(Boolean);
      setLines((prev) => [...prev, ...parts].slice(-200));
    };
    return () => es.close();
  }, []);

  return (
    <pre style={{ height: '90vh', overflow: 'auto', background: '#0b0b0b', color: '#8f8' }}>
{lines.join('\n')}
    </pre>
  );
}
