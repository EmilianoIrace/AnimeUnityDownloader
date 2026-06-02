"""Web GUI for AnimeUnityDownloader using FastAPI + SSE.

Run with:
    ./start.sh --web
or:
    .venv/bin/python3 web_gui.py
"""
from __future__ import annotations

import asyncio
import json
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_progress_queues: list[asyncio.Queue] = []
_download_lock = threading.Lock()
_is_downloading = False


class DownloadRequest(BaseModel):
    url: str
    start_episode: Optional[int] = None
    end_episode: Optional[int] = None
    download_path: str = "Downloads"


def _broadcast(event: dict) -> None:
    data = json.dumps(event)
    for q in list(_progress_queues):
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            pass


def _run_download(req: DownloadRequest) -> None:
    global _is_downloading
    import asyncio as _asyncio
    from anime_downloader import process_anime_download

    def callback(event: dict) -> None:
        _broadcast(event)

    try:
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        loop.run_until_complete(
            process_anime_download(
                req.url,
                start_episode=req.start_episode,
                end_episode=req.end_episode,
                download_path=req.download_path,
                progress_callback=callback,
            )
        )
        loop.close()
        _broadcast({"event": "done", "message": "Download completato con successo!"})
    except Exception as exc:
        _broadcast({"event": "error", "message": str(exc)})
    finally:
        with _download_lock:
            _is_downloading = False


@app.post("/download")
async def start_download(req: DownloadRequest):
    global _is_downloading
    with _download_lock:
        if _is_downloading:
            return {"ok": False, "message": "Download già in corso"}
        _is_downloading = True

    thread = threading.Thread(target=_run_download, args=(req,), daemon=True)
    thread.start()
    return {"ok": True}


@app.get("/progress")
async def progress_stream():
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _progress_queues.append(queue)

    async def event_generator():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {data}\n\n"
                    parsed = json.loads(data)
                    if parsed.get("event") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            _progress_queues.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/status")
async def status():
    return {"downloading": _is_downloading}


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=HTML)


HTML = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AnimeUnity Downloader</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0f0f13;
    color: #e0e0e8;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }

  .card {
    background: #1a1a24;
    border: 1px solid #2a2a3a;
    border-radius: 16px;
    padding: 36px 40px;
    width: 100%;
    max-width: 620px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.5);
  }

  h1 {
    font-size: 1.6rem;
    font-weight: 700;
    margin-bottom: 28px;
    background: linear-gradient(135deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .field { margin-bottom: 18px; }

  label {
    display: block;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
    margin-bottom: 6px;
  }

  input[type="text"], input[type="number"] {
    width: 100%;
    background: #12121a;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    color: #e0e0e8;
    font-size: 0.95rem;
    padding: 10px 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  input:focus { border-color: #7c3aed; }

  .row { display: flex; gap: 14px; }
  .row .field { flex: 1; }

  button#download-btn {
    width: 100%;
    margin-top: 8px;
    padding: 13px;
    background: linear-gradient(135deg, #7c3aed, #2563eb);
    border: none;
    border-radius: 10px;
    color: #fff;
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
  }
  button#download-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
  button#download-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  #status-bar {
    margin-top: 18px;
    font-size: 0.88rem;
    color: #888;
    min-height: 20px;
  }
  #status-bar.ok { color: #4ade80; }
  #status-bar.err { color: #f87171; }
  #status-bar.busy { color: #60a5fa; }

  #progress-section {
    margin-top: 22px;
    display: none;
  }

  #overall-bar-wrap {
    background: #12121a;
    border-radius: 6px;
    height: 8px;
    margin-bottom: 16px;
    overflow: hidden;
  }
  #overall-bar {
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #7c3aed, #2563eb);
    border-radius: 6px;
    transition: width 0.3s ease;
  }

  .ep-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }
  .ep-label {
    font-size: 0.78rem;
    color: #888;
    width: 64px;
    flex-shrink: 0;
  }
  .ep-bar-wrap {
    flex: 1;
    background: #12121a;
    border-radius: 4px;
    height: 6px;
    overflow: hidden;
  }
  .ep-bar {
    height: 100%;
    width: 0%;
    background: #7c3aed;
    border-radius: 4px;
    transition: width 0.2s ease;
  }
  .ep-bar.done { background: #4ade80; width: 100%; }
  .ep-pct {
    font-size: 0.75rem;
    color: #666;
    width: 36px;
    text-align: right;
    flex-shrink: 0;
  }
</style>
</head>
<body>
<div class="card">
  <h1>AnimeUnity Downloader</h1>

  <div class="field">
    <label for="url">URL Anime</label>
    <input type="text" id="url" placeholder="https://www.animeunity.so/anime/..." autocomplete="off">
  </div>

  <div class="row">
    <div class="field">
      <label for="start">Episodio iniziale</label>
      <input type="number" id="start" placeholder="1" min="1">
    </div>
    <div class="field">
      <label for="end">Episodio finale</label>
      <input type="number" id="end" placeholder="tutti" min="1">
    </div>
  </div>

  <div class="field">
    <label for="path">Cartella di download</label>
    <input type="text" id="path" value="Downloads">
  </div>

  <button id="download-btn" onclick="startDownload()">Scarica</button>

  <div id="status-bar">Pronto</div>

  <div id="progress-section">
    <div id="overall-bar-wrap"><div id="overall-bar"></div></div>
    <div id="episodes"></div>
  </div>
</div>

<script>
let eventSource = null;
let episodeBars = {};
let doneCount = 0;
let totalEpisodes = 0;

function setStatus(msg, cls) {
  const el = document.getElementById('status-bar');
  el.textContent = msg;
  el.className = cls || '';
}

function startDownload() {
  const url = document.getElementById('url').value.trim();
  if (!url) { setStatus('Inserisci un URL valido', 'err'); return; }

  const start = parseInt(document.getElementById('start').value) || null;
  const end   = parseInt(document.getElementById('end').value)   || null;
  const path  = document.getElementById('path').value.trim() || 'Downloads';

  if (start && end && start > end) {
    setStatus('Episodio iniziale deve essere ≤ episodio finale', 'err');
    return;
  }

  document.getElementById('download-btn').disabled = true;
  document.getElementById('progress-section').style.display = 'block';
  document.getElementById('episodes').innerHTML = '';
  document.getElementById('overall-bar').style.width = '0%';
  episodeBars = {};
  doneCount = 0;
  totalEpisodes = 0;
  setStatus('Avvio download…', 'busy');

  if (eventSource) { eventSource.close(); }
  eventSource = new EventSource('/progress');
  eventSource.onmessage = handleEvent;
  eventSource.onerror = () => {
    setStatus('Connessione SSE persa', 'err');
  };

  fetch('/download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, start_episode: start, end_episode: end, download_path: path })
  }).then(r => r.json()).then(d => {
    if (!d.ok) {
      setStatus(d.message, 'err');
      document.getElementById('download-btn').disabled = false;
    }
  });
}

function handleEvent(e) {
  let data;
  try { data = JSON.parse(e.data); } catch { return; }

  if (data.event === 'episode_progress') {
    const ep = data.episode;
    totalEpisodes = data.total;
    if (!episodeBars[ep]) { createEpBar(ep, data.total); }
    episodeBars[ep].bar.style.width = data.percent + '%';
    episodeBars[ep].pct.textContent = data.percent + '%';
  }

  if (data.event === 'episode_done') {
    const ep = data.episode;
    totalEpisodes = data.total;
    if (!episodeBars[ep]) { createEpBar(ep, data.total); }
    episodeBars[ep].bar.classList.add('done');
    episodeBars[ep].pct.textContent = '100%';
    doneCount++;
    updateOverall();
  }

  if (data.event === 'done') {
    setStatus(data.message, 'ok');
    document.getElementById('download-btn').disabled = false;
    if (eventSource) { eventSource.close(); eventSource = null; }
    updateOverall();
  }

  if (data.event === 'error') {
    setStatus('Errore: ' + data.message, 'err');
    document.getElementById('download-btn').disabled = false;
    if (eventSource) { eventSource.close(); eventSource = null; }
  }
}

function createEpBar(ep, total) {
  const wrap = document.getElementById('episodes');
  const row = document.createElement('div');
  row.className = 'ep-row';
  row.innerHTML = `
    <span class="ep-label">Ep ${ep}/${total}</span>
    <div class="ep-bar-wrap"><div class="ep-bar" id="bar-${ep}"></div></div>
    <span class="ep-pct" id="pct-${ep}">0%</span>
  `;
  wrap.appendChild(row);
  episodeBars[ep] = {
    bar: document.getElementById('bar-' + ep),
    pct: document.getElementById('pct-' + ep),
  };
}

function updateOverall() {
  if (!totalEpisodes) return;
  const pct = Math.round((doneCount / totalEpisodes) * 100);
  document.getElementById('overall-bar').style.width = pct + '%';
  setStatus(`${doneCount} / ${totalEpisodes} episodi completati`, 'busy');
}
</script>
</body>
</html>"""


def main(host: str = "127.0.0.1", port: int = 8765) -> None:
    url = f"http://{host}:{port}"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"AnimeUnity Downloader web GUI → {url}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
