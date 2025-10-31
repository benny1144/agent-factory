from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import json
import httpx

router = APIRouter()

# Simple in-browser chat HTML/JS client
@router.get("/", response_class=HTMLResponse)
async def chat_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>🜂 Archy Chat</title>
      <style>
        body { font-family: Arial, sans-serif; background:#111; color:#eee; margin:0; display:flex; flex-direction:column; height:100vh; }
        #log { flex:1; overflow-y:auto; padding:1em; }
        #input { display:flex; border-top:1px solid #333; }
        input[type=text] { flex:1; padding:.5em; background:#222; color:#eee; border:none; outline:none; }
        button { background:#444; color:#eee; border:none; padding:.5em 1em; cursor:pointer; }
        button:hover { background:#666; }
        .user { color:#aef; margin:.25em 0; }
        .bot { color:#afa; margin:.25em 0; }
      </style>
    </head>
    <body>
      <div id="log"><div class="bot">🜂 Archy is online.</div></div>
      <div id="input">
        <input id="msg" type="text" placeholder="Type a message... (Enter to send)">
        <button onclick="send()">Send</button>
        <input id="file" type="file" style="margin-left:.5em;">
        <button onclick="upload()">Upload</button>
      </div>
      <script>
        const log = document.getElementById('log');
        const msg = document.getElementById('msg');
        const fileInput = document.getElementById('file');

        async function send() {
          const text = msg.value.trim();
          if(!text) return;
          append('user','🧑 '+text);
          msg.value='';
          const res = await fetch('/chat', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({message:text})
          });
          const data = await res.json();
          append('bot','🜂 '+data.reply);
        }

        async function upload() {
          if(!fileInput.files || fileInput.files.length===0){ return; }
          const fd = new FormData();
          fd.append('file', fileInput.files[0]);
          append('user', '🧑 [upload] '+fileInput.files[0].name);
          const res = await fetch('/upload', { method:'POST', body: fd });
          const data = await res.json();
          if(data.status==='success'){
            append('bot', '🜂 '+(data.reply || ('📂 File uploaded: '+data.path)));
          } else {
            append('bot','🜂 Upload failed: '+(data.detail||data.error||'unknown'));
          }
          fileInput.value='';
        }

        msg.addEventListener('keypress', e=>{ if(e.key==='Enter'){ send(); }});

        function append(role,text){
          const div=document.createElement('div');
          div.className=role;
          div.textContent=text;
          log.appendChild(div);
          log.scrollTop=log.scrollHeight;
        }
      </script>
    </body>
    </html>
    """

