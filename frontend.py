import os

import httpx
import logging
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# --- logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("frontend")

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8888")
app = FastAPI(title="Best Question Picker — Front")

logger.info(f"Frontend app started. BACKEND_URL={BACKEND_URL}")

# --- HTML (встроенный шаблон) ---
INDEX_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Выбор лучшего вопроса — UI</title>
  <style>
    :root { --fg:#0f172a; --muted:#475569; --bg:#f8fafc; --prim:#2563eb; --ok:#16a34a; --warn:#b45309; --err:#dc2626; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans"; background: var(--bg); color: var(--fg); }
    .wrap { max-width: 1100px; margin: 24px auto; padding: 0 16px; }
    h1 { font-size: 22px; margin: 0 0 16px; }
    .card { background:#fff; border:1px solid #e5e7eb; border-radius: 14px; box-shadow: 0 2px 10px rgba(2,8,23,.04); padding:16px; }
    .row { display:flex; gap:12px; flex-wrap: wrap; }
    .field { display:flex; flex-direction: column; gap:6px; min-width: 240px; }
    label { font-size: 12px; color: var(--muted); }
    input, select, textarea { border:1px solid #e5e7eb; border-radius: 10px; padding:10px 12px; font-size:14px; background:#fff; }
    input[type="checkbox"] { width:auto; scale:1.1; }
    button { border:1px solid var(--prim); background: var(--prim); color:#fff; padding:10px 14px; border-radius: 12px; font-weight:600; cursor:pointer; }
    button.secondary { background:#fff; color: var(--prim); }
    button:disabled { opacity:.6; cursor:not-allowed; }
    .actions { display:flex; gap:10px; align-items:center; flex-wrap: wrap; }
    .status { font-size:12px; color: var(--muted); }
    table { width:100%; border-collapse: collapse; }
    thead th { position: sticky; top:0; background:#f1f5f9; z-index:1; }
    th, td { text-align:left; padding:8px 10px; border-bottom:1px solid #e5e7eb; vertical-align: top; }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; border:1px solid #e2e8f0; background:#f8fafc; }
    .grid { display:grid; grid-template-columns: 1fr; gap:16px; }
    @media (min-width: 900px) { .grid { grid-template-columns: 1fr 1fr; } }
    pre { white-space: pre-wrap; word-break: break-word; background:#0b1220; color:#e2e8f0; padding:12px; border-radius: 12px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    .muted { color: var(--muted); }
    .winner { border-left: 4px solid var(--ok); padding-left: 12px; }
    .error { color: var(--err); }
    .search { margin-left:auto; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Выбор лучшего вопроса (клиент к /pick_best_question)</h1>

    <div class="card" style="margin-bottom:16px">
      <div class="row">
        <div class="field">
          <label>Часовой пояс (IANA)</label>
          <input id="tz" type="text" value="Europe/Amsterdam" />
        </div>
        <div class="field">
          <label>Начало периода</label>
          <input id="start" type="datetime-local" />
        </div>
        <div class="field">
          <label>Конец периода</label>
          <input id="end" type="datetime-local" />
        </div>
        <div class="field">
          <label>Лимит кандидатов</label>
          <input id="limit" type="number" min="1" step="1" value="1000" />
        </div>
        <div class="field">
          <label>Фильтр</label>
          <div style="display:flex; gap:16px; align-items:center; padding-top:8px">
            <label class="mono"><input id="use_prescoring" type="checkbox" /> use_prescoring</label>
            <label class="mono"><input id="dedupe" type="checkbox" checked /> dedupe</label>
          </div>
        </div>
      </div>
      <div class="actions" style="margin-top:12px">
        <button id="btnCandidatesOnly" class="secondary">Только кандидаты</button>
        <button id="btnPickBest">Выбрать лучший (через LLM)</button>
        <span id="status" class="status"></span>
        <div class="search">
          <input id="search" type="text" placeholder="поиск по тексту…" />
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h3 style="margin-top:0">Итог</h3>
        <div id="summary" class="muted">Нет данных</div>
        <div id="winner" class="winner" style="margin-top:10px; display:none"></div>
      </div>

      <div class="card">
        <h3 style="margin-top:0">Сырой ответ LLM</h3>
        <pre id="raw"></pre>
      </div>
    </div>

    <div class="card" style="margin-top:16px">
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px">
        <h3 style="margin:0">Кандидаты</h3>
        <span id="cnt" class="pill">0</span>
      </div>
      <div style="overflow:auto; max-height: 60vh">
        <table id="table">
          <thead>
            <tr>
              <th>#</th>
              <th>msg_id</th>
              <th>chat_id</th>
              <th>time (UTC)</th>
              <th>is_question</th>
              <th>prescore</th>
              <th>content</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
  </div>

<script>
  const $ = sel => document.querySelector(sel);
  function toInputLocal(dt) {
    const pad = n => String(n).padStart(2, '0');
    return `${dt.getFullYear()}-${pad(dt.getMonth()+1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
  }
  document.addEventListener('DOMContentLoaded', () => {
    const end = new Date();
    const start = new Date(end.getTime() - 6*60*60*1000);
    $('#start').value = toInputLocal(start);
    $('#end').value = toInputLocal(end);
  });

  function uiBusy(b) {
    $('#btnCandidatesOnly').disabled = b; $('#btnPickBest').disabled = b;
    $('#status').textContent = b ? 'выполняю…' : '';
  }
  function escapeHtml(s){ return String(s||'').replace(/[&<>\\\"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\\"":"&quot;"}[c])); }

  let lastResponse = null;
  const render0 = (res) => {
    $('#cnt').textContent = (res?.candidates_count ?? 0);
    const s = [];
    s.push(`Кандидатов: ${res?.candidates_count ?? 0}`);
    if (res?.winner_msg_id) s.push(`Победитель: ${res.winner_msg_id}`);
    $('#summary').textContent = s.join(' · ');

    if (res?.winner_msg_id) {
      $('#winner').style.display = '';
      $('#winner').innerHTML = `<div class="mono">msg_id: <b>${escapeHtml(res.winner_msg_id)}</b></div>
                                 <div style="margin:6px 0 8px 0"><b>${escapeHtml(res.winner_content||'')}</b></div>
                                 <div class="muted">Причина: ${escapeHtml(res.model_reason||'—')}</div>`;
    } else { $('#winner').style.display='none'; $('#winner').innerHTML=''; }

    $('#raw').textContent = res?.raw_model_output || '';

    const tbody = $('#table tbody');
    tbody.innerHTML = '';
    const q = ($('#search').value||'').toLowerCase();
    (res?.candidates||[]).forEach(c => {
      if (q && !(`${c.msg_id} ${c.chat_id} ${c.content}`.toLowerCase().includes(q))) return;
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="mono">${c.rank}</td>
                      <td class="mono">${escapeHtml(c.msg_id)}</td>
                      <td class="mono">${escapeHtml(c.chat_id)}</td>
                      <td class="mono">${escapeHtml(c.created_at_iso)}</td>
                      <td>${c.is_question ? '✓' : '—'}</td>
                      <td class="mono">${c.prescore??''}</td>
                      <td>${escapeHtml(c.content)}</td>`;
      tbody.appendChild(tr);
    });
  };
  function render(res){ lastResponse = res; render0(res); }

  async function call(returnCandidatesOnly){
    try {
      uiBusy(true);
      const payload = {
        start: $('#start').value.replace('T',' '),
        end: $('#end').value.replace('T',' '),
        tz: $('#tz').value || 'Europe/Amsterdam',
        candidate_limit: Math.max(1, parseInt($('#limit').value||'1000',10)),
        use_prescoring: $('#use_prescoring').checked,
        dedupe: $('#dedupe').checked,
        return_candidates_only: !!returnCandidatesOnly,
      };
      const r = await fetch('/api/pick_best_question', {
        method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      render(await r.json());
    } catch (e) {
      $('#summary').innerHTML = `<span class="error">Ошибка: ${escapeHtml(e.message||String(e))}</span>`;
    } finally { uiBusy(false); }
  }

  $('#btnCandidatesOnly').addEventListener('click', ()=> call(true));
  $('#btnPickBest').addEventListener('click', ()=> call(false));
  $('#search').addEventListener('input', ()=>{ if (lastResponse) render0(lastResponse); });
</script>
</body>
</html>
"""


# --- Роуты ---
@app.get("/", response_class=HTMLResponse)
async def index():
    logger.debug("Serving index.html")
    return HTMLResponse(INDEX_HTML)


@app.post("/api/pick_best_question")
async def proxy_pick_best(request: Request):
    """
    Проксируем на BACKEND_URL/pick_best_question,
    чтобы фронт и API были на одном origin (никакого CORS).
    """
    logger.info("Received request at /api/pick_best_question")
    try:
        payload = await request.json()
        logger.debug(f"Parsed JSON payload: {payload}")
    except Exception as e:
        logger.error(f"Failed to parse JSON body: {e}")
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    url = f"{BACKEND_URL.rstrip('/')}/pick_best_question"
    logger.info(f"Forwarding request to backend: {url}")

    timeout = httpx.Timeout(30.0, read=60.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload)
            logger.info(f"Backend response status: {resp.status_code}")
            logger.debug(f"Backend response headers: {resp.headers}")
            # если надо логировать контент, осторожно с большим телом:
            logger.debug(f"Backend response content (truncated): {resp.text[:500]}")
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "application/json"),
            )
        except httpx.RequestError as e:
            logger.error(f"Failed to reach backend: {e}")
            return JSONResponse({"error": f"backend unreachable: {str(e)}"}, status_code=502)
        except Exception as e:
            logger.exception("Unexpected error during proxy call")
            return JSONResponse({"error": f"unexpected error: {str(e)}"}, status_code=500)