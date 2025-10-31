import React, { useState, useEffect } from "react";

export default function Chatroom() {
  const [messages, setMessages] = useState<string[]>([]);
  const [input, setInput] = useState("");

  useEffect(() => {
    const evtSource = new EventSource("/logs/stream");
    evtSource.onmessage = (e) => setMessages((m) => [...m, e.data]);
    return () => evtSource.close();
  }, []);

  const sendMessage = async () => {
    if (!input.trim()) return;
    await fetch("/orion/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: input })
    });
    setInput("");
  };

  return (
    <div className="p-4 bg-black text-green-400 font-mono h-full">
      <div className="overflow-y-auto h-96 border p-2">
        {messages.map((m, i) => (
          <div key={i}>{m}</div>
        ))}
      </div>
      <input
        className="w-3/4 p-2 text-black"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') sendMessage();
        }}
      />
      <button onClick={sendMessage} className="p-2 bg-green-700 text-white">Send</button>
    </div>
  );
}
