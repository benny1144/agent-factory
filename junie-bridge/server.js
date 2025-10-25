// server.js
// ---------------------------------------------------------------------------
// Junie Bridge: local API that lets GPT and IntelliJ ("Junie") talk.
// Cross-platform. Includes HITL /ui page with token prompt.
// ---------------------------------------------------------------------------

const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const fs = require('fs');
const fsp = fs.promises;
const path = require('path');
const { spawn } = require('child_process');
const fg = require('fast-glob');
const { nanoid } = require('nanoid');
require('dotenv').config({ path: path.join(__dirname, '.env') });

const app = express();
app.use(cors());
app.use((req,res,next)=>{ req.url = req.url.replace(/\/{2,}/g,'/'); next(); });
app.use((req,res,next)=>{ console.log(`[REQ] ${req.method} ${req.path}`); next(); });
app.use(bodyParser.json({ limit: '20mb' }));

const PORT = process.env.PORT || 8765;
const TOKEN = process.env.JUNIE_TOKEN || process.env.BRIDGE_TOKEN || 'dev';
const TOKEN_REQUIRED = String(process.env.TOKEN_REQUIRED || '').toLowerCase() === 'true';
const projectRoot = process.cwd();

const safeJoin = (rel) => path.normalize(path.join(projectRoot, rel || ''));
const exists = async (p) => !!(await fsp.stat(p).catch(() => null));

// ---------------------------------------------------------------------------
//  AUTH (allow /ui without token)
// ---------------------------------------------------------------------------
app.use((req, res, next) => {
  if (req.method === 'GET' && (req.path === '/health' || req.path === '/ui')) return next();
  const got = req.header('X-Junie-Token') || req.query.token;
  if (!TOKEN || got === TOKEN) return next();
  res.status(401).json({ error: 'unauthorized' });
});

// ---------------------------------------------------------------------------
//  IN-MEMORY MESSAGE STORE
// ---------------------------------------------------------------------------
const messages = [];
function addMessage({ role, text, inReplyToId = null, status = 'queued' }) {
    const msg = {
        id: nanoid(12),
        role,
        text,
        inReplyToId,
        status,
        createdAt: new Date().toISOString(),
    };
    messages.push(msg);
    return msg;
}

// ---------------------------------------------------------------------------
//  BASIC ENDPOINTS
// ---------------------------------------------------------------------------
app.get('/health', (req, res) => {
    res.json({ ok: true, status: 'healthy', service: 'Junie Bridge' });
});

app.get('/project', async (req, res) => {
    res.json({
        name: path.basename(projectRoot),
        rootPath: projectRoot,
        languages: [],
        vcs: 'git',
    });
});

// ---------------------------------------------------------------------------
//  FILE TREE
// ---------------------------------------------------------------------------
async function listDir(dir, depth, includeHidden) {
    const items = await fsp.readdir(dir, { withFileTypes: true });
    const results = [];
    for (const it of items) {
        if (!includeHidden && it.name.startsWith('.')) continue;
        const full = path.join(dir, it.name);
        const stat = await fsp.stat(full);
        const entry = {
            path: path.relative(projectRoot, full),
            type: it.isDirectory() ? 'dir' : 'file',
            size: stat.size,
            modifiedAt: stat.mtime.toISOString(),
        };
        results.push(entry);
        if (it.isDirectory() && (depth > 0 || depth === -1)) {
            const sub = await listDir(full, depth === -1 ? -1 : depth - 1, includeHidden);
            results.push(...sub);
        }
    }
    return results;
}

app.get('/tree', async (req, res) => {
    try {
        const rel = req.query.path || '';
        const depthReq = req.query.depth ?? 3;
        const depth = Number(depthReq);
        const includeHidden = req.query.includeHidden === 'true';
        const dir = safeJoin(rel);
        if (!(await exists(dir))) return res.status(404).json({ error: 'not_found', detail: 'Path not found' });
        const list = await listDir(dir, isNaN(depth) ? 3 : depth, includeHidden);
        res.json({ entries: list });
    } catch (e) {
        res.status(500).json({ error: 'server_error', detail: String(e) });
    }
});

// ---------------------------------------------------------------------------
//  FILES: READ / WRITE
// ---------------------------------------------------------------------------
app.get('/files/content', async (req, res) => {
    try {
        const rel = req.query.path;
        if (!rel) return res.status(400).json({ error: 'bad_request', detail: 'path is required' });
        const full = safeJoin(rel);
        const enc = (req.query.encoding || 'utf-8').toLowerCase();
        const buf = await fsp.readFile(full);
        if (enc === 'base64') {
            res.json({ path: rel, encoding: 'base64', content: buf.toString('base64') });
        } else {
            res.json({ path: rel, encoding: 'utf-8', content: buf.toString('utf-8') });
        }
    } catch (e) {
        if (e.code === 'ENOENT') return res.status(404).json({ error: 'not_found', detail: 'File not found' });
        res.status(500).json({ error: 'server_error', detail: String(e) });
    }
});

app.post('/files/write', async (req, res) => {
    try {
        const { path: rel, content, encoding = 'utf-8', createDirs = true, overwrite = true } = req.body || {};
        if (!rel || typeof content !== 'string') {
            return res.status(400).json({ error: 'bad_request', detail: 'path and content required' });
        }
        const full = safeJoin(rel);
        if (!overwrite && await exists(full)) {
            return res.status(409).json({ error: 'conflict', detail: 'File exists and overwrite=false' });
        }
        if (createDirs) await fsp.mkdir(path.dirname(full), { recursive: true });
        const data = encoding === 'base64' ? Buffer.from(content, 'base64') : content;
        await fsp.writeFile(full, data);
        const bytes = encoding === 'base64' ? data.length : Buffer.byteLength(data, 'utf-8');
        res.json({ path: rel, bytes, created: true });
    } catch (e) {
        res.status(500).json({ error: 'server_error', detail: String(e) });
    }
});

// ---------------------------------------------------------------------------
//  SEARCH
// ---------------------------------------------------------------------------
app.post('/search', async (req, res) => {
    try {
        const { query, regex = false, caseSensitive = false, glob = ['**/*'], maxResults = 200 } = req.body || {};
        if (!query) return res.status(400).json({ error: 'bad_request', detail: 'query required' });
        const paths = await fg(glob, {
            cwd: projectRoot,
            gitignore: true, // respect .gitignore
            dot: false,      // skip dotfiles
            onlyFiles: true,
            unique: true
        });
        const results = [];
        const re = regex ? new RegExp(query, caseSensitive ? '' : 'i') : null;

        for (const p of paths) {
            const full = safeJoin(p);
            const st = await fsp.stat(full).catch(() => null);
            if (!st || st.isDirectory() || st.size > 2_000_000) continue;
            const content = await fsp.readFile(full, 'utf8').catch(() => null);
            if (!content) continue;

            const lines = content.split('\n');
            for (let i = 0; i < lines.length; i++) {
                const lineText = lines[i];
                const match = re ? re.test(lineText) : (caseSensitive ? lineText.includes(query) : lineText.toLowerCase().includes(query.toLowerCase()));
                if (match) {
                    results.push({
                        path: p,
                        line: i + 1,
                        column: Math.max(1, (lineText.indexOf(query) + 1) || 1),
                        match: lineText.trim(),
                        contextBefore: lines.slice(Math.max(0, i - 2), i),
                        contextAfter: lines.slice(i + 1, i + 3),
                    });
                    if (results.length >= maxResults) break;
                }
            }
            if (results.length >= maxResults) break;
        }
        res.json({ results });
    } catch (e) {
        res.status(500).json({ error: 'server_error', detail: String(e) });
    }
});

// ---------------------------------------------------------------------------
//  OPEN FILE IN INTELLIJ
// ---------------------------------------------------------------------------
app.post('/ide/open', async (req, res) => {
    try {
        const { path: rel, line = 1 } = req.body || {};
        if (!rel) return res.status(400).json({ error: 'bad_request', detail: 'path is required' });
        const full = safeJoin(rel);

        // Use IDEA_LAUNCHER if provided in .env (recommended on Windows)
        let launcher = process.env.IDEA_LAUNCHER;
        const isWin = process.platform === 'win32';
        let args = ['--line', String(line), full];

        if (!launcher) {
            if (isWin) {
                // Try idea.bat first; if not found on PATH, try idea64.exe
                try {
                    const foundBat = require('child_process').spawnSync('where', ['idea.bat'], { shell: true });
                    if (foundBat.status === 0) {
                        launcher = 'idea.bat';
                    } else {
                        const foundExe = require('child_process').spawnSync('where', ['idea64.exe'], { shell: true });
                        launcher = (foundExe.status === 0) ? 'idea64.exe' : 'idea.bat';
                    }
                } catch (e) {
                    launcher = 'idea.bat';
                }
            } else {
                launcher = 'idea';
            }
        }

        const child = spawn(launcher, args, {
            detached: true,
            stdio: 'ignore',
            shell: isWin // allow .bat with spaces in path
        });
        child.unref();

        res.json({ ok: true });
    } catch (e) {
        res.status(500).json({ error: 'server_error', detail: String(e) });
    }
});

// ---------------------------------------------------------------------------
//  MESSAGES
// ---------------------------------------------------------------------------
app.post('/messages/send', (req, res) => {
    const { role = 'gpt', text, inReplyToId = null } = req.body || {};
    if (!text) return res.status(400).json({ error: 'bad_request', detail: 'text required' });
    if (!['gpt', 'human'].includes(role)) return res.status(400).json({ error: 'bad_request', detail: 'role must be gpt or human' });
    const msg = addMessage({ role, text, inReplyToId, status: 'queued' });
    res.json(msg);
});

app.get('/messages/pull', (req, res) => {
    const { sinceId, since, max = 50, roles } = req.query || {};
    let out = messages.slice();
    if (roles) {
        const set = new Set(String(roles).split(',').map(s => s.trim()));
        out = out.filter(m => set.has(m.role));
    }
    if (since) {
        const t = Date.parse(since);
        if (!isNaN(t)) out = out.filter(m => Date.parse(m.createdAt) > t);
    }
    if (sinceId) {
        const idx = out.findIndex(m => m.id === sinceId);
        if (idx >= 0) out = out.slice(idx + 1);
    }
    res.json({ messages: out.slice(-Number(max)) });
});

// Lightweight search: check if any message matches a substring and optional status
app.get('/messages/has', (req, res) => {
    try {
        const q = String(req.query.q || '').trim();
        const status = (req.query.status || '').toString().trim();
        let list = messages.slice();
        if (status) list = list.filter(m => String(m.status) === status);
        if (q) {
            const needle = q.toLowerCase();
            list = list.filter(m => (m.text || '').toLowerCase().includes(needle));
        }
        res.json({ has: list.length > 0, count: list.length });
    } catch (e) {
        res.status(500).json({ error: 'server_error', detail: String(e) });
    }
});

app.post('/messages/ack', (req, res) => {
    const { ids } = req.body || {};
    if (!Array.isArray(ids)) return res.status(400).json({ error: 'bad_request', detail: 'ids array required' });
    for (const id of ids) {
        const m = messages.find(mm => mm.id === id);
        if (m) m.status = 'read';
    }
    res.json({ ok: true });
});

app.post('/messages/hitl/ingest', (req, res) => {
    const { text, inReplyToId = null } = req.body || {};
    if (!text) return res.status(400).json({ error: 'bad_request', detail: 'text required' });
    const msg = addMessage({ role: 'junie', text, inReplyToId, status: 'delivered' });
    res.json(msg);
});

// ---------------------------------------------------------------------------
//  SIMPLE WEB UI (HITL)
// ---------------------------------------------------------------------------
app.get('/ui', (req, res) => {
    const html = [
        '<!doctype html>',
        '<html>',
        '<head>',
        '<meta charset="utf-8" />',
        '<title>Junie Bridge UI</title>',
        '<style>',
        '  body { font-family: system-ui, sans-serif; margin: 20px; }',
        '  .row { display: flex; gap: 16px; }',
        '  textarea { width: 100%; height: 120px; }',
        '  .col { flex: 1; min-width: 320px; }',
        '  .log { border: 1px solid #ddd; padding: 8px; height: 260px; overflow: auto; background: #fafafa; }',
        '  .msg { border-bottom: 1px dashed #ddd; padding: 6px 0; }',
        '  .role { font-weight: bold; }',
        '  .controls { margin: 8px 0; display:flex; gap:8px; flex-wrap: wrap; }',
        '  input[type=text] { width: 100%; padding: 6px; }',
        '  small { color: #666; }',
        '</style>',
        '</head>',
        '<body>',
        '  <h2>Junie Bridge UI</h2>',
        '  <div class="row">',
        '    <div class="col">',
        '      <h3>Send instruction to Junie (from GPT/Human)</h3>',
        '      <textarea id="outText" placeholder="Type an instruction for Junie..."></textarea>',
        '      <div class="controls">',
        '        <select id="role">',
        '          <option value="gpt">gpt</option>',
        '          <option value="human">human</option>',
        '        </select>',
        '        <button id="sendBtn">Send</button>',
        '      </div>',
        '    </div>',
        '    <div class="col">',
        '      <h3>Paste Junie\'s reply (HITL)</h3>',
        '      <textarea id="inText" placeholder="Paste Junie\'s reply here..."></textarea>',
        '      <div class="controls">',
        '        <button id="ingestBtn">Ingest Reply</button>',
        '      </div>',
        '    </div>',
        '  </div>',
        '  <h3>Messages</h3>',
        '  <div class="controls">',
        '    <button id="refreshBtn">Refresh</button>',
        '  </div>',
        '  <div id="log" class="log"></div>',
        '',
        '<script>',
        'let TOKEN = localStorage.getItem("JUNIE_TOKEN") || "";',
        'async function ensureToken() {',
        '  if (!TOKEN) {',
        '    TOKEN = prompt("Enter X-Junie-Token (from your .env JUNIE_TOKEN):", "");',
        '    if (TOKEN) localStorage.setItem("JUNIE_TOKEN", TOKEN);',
        '  }',
        '}',
        'async function api(path, options = {}) {',
        '  await ensureToken();',
        '  options.headers = Object.assign({}, options.headers, {',
        '    "X-Junie-Token": TOKEN',
        '  });',
        '  const res = await fetch(path, options);',
        '  if (res.status === 401) {',
        '    localStorage.removeItem("JUNIE_TOKEN");',
        '    TOKEN = "";',
        '    alert("Unauthorized. Please re-enter your token.");',
        '    throw new Error("unauthorized");',
        '  }',
        '  return res;',
        '}',
        '',
        'async function fetchMessages() {',
        '  const res = await api("/messages/pull?max=200");',
        '  const data = await res.json();',
        '  const log = document.getElementById("log");',
        '  log.innerHTML = "";',
        '  for (const m of data.messages) {',
        '    const div = document.createElement("div");',
        '    div.className = "msg";',
        '    div.innerHTML = "<span class=\\"role\\">[" + m.role + "]</span> " + m.text +',
        '      "<br><small>" + m.createdAt + " · id:" + m.id + " · status:" + m.status + "</small>";',
        '    log.appendChild(div);',
        '  }',
        '  log.scrollTop = log.scrollHeight;',
        '}',
        'document.getElementById("refreshBtn").onclick = fetchMessages;',
        '',
        'document.getElementById("sendBtn").onclick = async () => {',
        '  const text = document.getElementById("outText").value.trim();',
        '  const role = document.getElementById("role").value;',
        '  if (!text) return alert("Enter some text");',
        '  await api("/messages/send", {',
        '    method: "POST", headers: { "Content-Type": "application/json" },',
        '    body: JSON.stringify({ role, text })',
        '  });',
        '  document.getElementById("outText").value = "";',
        '  fetchMessages();',
        '};',
        '',
        'document.getElementById("ingestBtn").onclick = async () => {',
        '  const text = document.getElementById("inText").value.trim();',
        '  if (!text) return alert("Paste Junie reply first");',
        '  await api("/messages/hitl/ingest", {',
        '    method: "POST", headers: { "Content-Type": "application/json" },',
        '    body: JSON.stringify({ text })',
        '  });',
        '  document.getElementById("inText").value = "";',
        '  fetchMessages();',
        '};',
        '',
        'fetchMessages();',
        '</script>',
        '</body>',
        '</html>'
    ].join('\n');

    res.type('html').send(html);
});

// ---------------------------------------------------------------------------
//  START SERVER
// ---------------------------------------------------------------------------
const https = require('https');
const tls = require('tls');

function start() {
  const useHttps = String(process.env.USE_HTTPS || '').toLowerCase() === 'true';
  const envPort = process.env.PORT || 8765;
  const httpPort = useHttps && String(envPort) === '443' ? 8765 : envPort;

  // Always start HTTP server for local tools/health checks
  app.listen(httpPort, () => {
    console.log(`🚀 Junie Bridge (HTTP) on http://localhost:${httpPort}`);
    console.log(`Project root: ${projectRoot}`);
    console.log(`Token required: ${TOKEN ? 'Yes' : 'No'}`);
    if (useHttps && String(envPort) === '443' && String(httpPort) !== String(envPort)) {
      console.log(`Note: USE_HTTPS=true and PORT=443; started HTTP on ${httpPort} for compatibility.`);
    }
  });

  if (useHttps) {
    // Resolve cert/key relative to this file if given as relative paths
    const certPath = path.isAbsolute(process.env.HTTPS_CERT)
      ? process.env.HTTPS_CERT
      : path.join(__dirname, process.env.HTTPS_CERT || 'certs/localhost.pem');

    const keyPath = path.isAbsolute(process.env.HTTPS_KEY)
      ? process.env.HTTPS_KEY
      : path.join(__dirname, process.env.HTTPS_KEY || 'certs/localhost-key.pem');

    const options = {
      cert: fs.readFileSync(certPath),
      key: fs.readFileSync(keyPath),
      minVersion: 'TLSv1.2',
      honorCipherOrder: true,
      secureOptions: tls.SSL_OP_NO_RENEGOTIATION
    };

    const httpsPort = Number(process.env.HTTPS_PORT || envPort || 443);
    const fallbackPort = Number(process.env.HTTPS_FALLBACK_PORT || 0);

    const httpsServer = https.createServer(options, app);
    httpsServer.on('error', (err) => {
      if (err && err.code === 'EADDRINUSE') {
        console.error(`HTTPS port ${httpsPort} is already in use (EADDRINUSE).`);
        if (fallbackPort && fallbackPort !== httpsPort) {
          try {
            httpsServer.listen(fallbackPort, () => {
              console.log(`🔐 Junie Bridge (HTTPS) on https://localhost:${fallbackPort} (fallback)`);
            });
          } catch (e) {
            console.error('Failed to bind fallback HTTPS port:', e);
          }
        } else {
          console.warn('No HTTPS_FALLBACK_PORT set; continuing without HTTPS. HTTP remains available.');
        }
      } else {
        console.error('HTTPS server error:', err);
      }
    });

    httpsServer.listen(httpsPort, () => {
      console.log(`🔐 Junie Bridge (HTTPS) on https://localhost:${httpsPort}`);
    });
  }
}

start();

