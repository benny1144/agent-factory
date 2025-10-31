import express from 'express';
import fs from 'fs';
import path from 'path';

const app = express();
app.use(express.json());

const repoRoot = path.resolve(__dirname, '../../..');
const logsDir = path.join(repoRoot, 'logs');
const orionLog = path.join(logsDir, 'orion_activity.jsonl');
const artisanLog = path.join(logsDir, 'artisan_activity.jsonl');
const genesisLog = path.join(logsDir, 'genesis_activity.jsonl');
const tasksFromOrion = path.join(repoRoot, 'tasks', 'from_orion');
const pendingHuman = path.join(repoRoot, 'tasks', 'pending_human');
const eventBus = path.join(repoRoot, 'governance', 'event_bus.jsonl');
const govAudit = path.join(repoRoot, 'logs', 'governance', 'orion_audit.jsonl');

// Ensure directories exist
fs.mkdirSync(logsDir, { recursive: true });
fs.mkdirSync(tasksFromOrion, { recursive: true });
fs.mkdirSync(pendingHuman, { recursive: true });
fs.mkdirSync(path.dirname(eventBus), { recursive: true });

app.get('/logs/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const send = () => {
    try {
      const collect = (p: string) => (fs.existsSync(p) ? fs.readFileSync(p, 'utf-8').split('\n').filter(Boolean) : []);
      const merged = [
        ...collect(orionLog),
        ...collect(artisanLog),
        ...collect(genesisLog),
      ];
      if (merged.length === 0) return;
      const chunk = merged.slice(-100).join('\n');
      res.write(`data: ${chunk}\n\n`);
    } catch (e) {
      // ignore
    }
  };

  send();
  const interval = setInterval(send, 2000);
  req.on('close', () => clearInterval(interval));
});

// Governance event bus stream (SSE)
app.get('/gov/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const send = () => {
    try {
      if (!fs.existsSync(eventBus)) return;
      const lines = fs.readFileSync(eventBus, 'utf-8').split('\n').filter(Boolean);
      const tail = lines.slice(-200).join('\n');
      res.write(`data: ${tail}\n\n`);
    } catch (e) {
      // ignore
    }
  };

  send();
  const interval = setInterval(send, 2000);
  req.on('close', () => clearInterval(interval));
});

app.post('/orion/send', (req, res) => {
  const msg = String(req.body?.message || '').trim();
  if (!msg) {
    res.status(400).json({ ok: false, error: 'message required' });
    return;
  }
  const payload = {
    ts: new Date().toISOString(),
    type: 'watchtower_message',
    message: msg,
    source: 'watchtower',
  };
  const file = path.join(tasksFromOrion, `${Date.now()}.json`);
  fs.writeFileSync(file, JSON.stringify(payload, null, 2));
  res.json({ ok: true, data: { file } });
});

// Approval endpoint: mark a pending human task as approved
app.post('/orion/approve', (req, res) => {
  const id = String(req.body?.id || '').trim();
  if (!id) {
    res.status(400).json({ ok: false, error: 'id required' });
    return;
  }
  const marker = path.join(pendingHuman, `${id}.approved`);
  try {
    fs.writeFileSync(marker, JSON.stringify({ ts: new Date().toISOString(), id }, null, 2));
    res.json({ ok: true, data: { marker } });
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

// List pending human approvals
app.get('/pending/list', (_req, res) => {
  try {
    const files = fs.readdirSync(pendingHuman)
      .filter((f) => f.endsWith('.awaiting'))
      .map((f) => ({ id: path.basename(f, '.awaiting'), file: path.join(pendingHuman, f) }));
    res.json({ ok: true, data: { pending: files } });
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

// Fetch Orion chat log
app.get('/logs/chat/watchtower_room.jsonl', (_req, res) => {
  try {
    const chatPath = path.join(logsDir, 'chat', 'watchtower_room.jsonl');
    fs.mkdirSync(path.dirname(chatPath), { recursive: true });
    if (!fs.existsSync(chatPath)) {
      fs.writeFileSync(chatPath, '');
    }
    const text = fs.readFileSync(chatPath, 'utf-8');
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.send(text);
  } catch (e: any) {
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.send('');
  }
});

// Governance audit file endpoints
app.get('/gov/audit', (_req, res) => {
  try {
    fs.mkdirSync(path.dirname(govAudit), { recursive: true });
    if (!fs.existsSync(govAudit)) fs.writeFileSync(govAudit, '');
    const text = fs.readFileSync(govAudit, 'utf-8');
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.send(text);
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.get('/gov/audit/status', (_req, res) => {
  try {
    const text = fs.existsSync(govAudit) ? fs.readFileSync(govAudit, 'utf-8') : '';
    const lines = text.split('\n').filter(Boolean);
    let active = false;
    if (lines.length) {
      try {
        const last = JSON.parse(lines[lines.length - 1]);
        active = String(last?.telemetry || '').toUpperCase() === 'ACTIVE';
      } catch {
        active = false;
      }
    }
    res.json({ ok: true, active });
  } catch (e: any) {
    res.status(200).json({ ok: true, active: false });
  }
});

const PORT = 8001;
app.listen(PORT, () => console.log(`🜂 Watchtower API running on port ${PORT}`));
