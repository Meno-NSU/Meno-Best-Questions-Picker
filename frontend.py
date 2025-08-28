import logging
import os

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

# --- logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("frontend")

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8888")
app = FastAPI(title="Best Question Picker — Front")

logger.info(f"Frontend app started. BACKEND_URL={BACKEND_URL}")

# --- HTML (inline) ---
INDEX_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Выбор лучшего вопроса — UI</title>
  <style>
    :root { --fg:#0f172a; --muted:#475569; --bg:#f8fafc; --prim:#2563eb; --ok:#16a34a; --warn:#b45309; --err:#dc2626; --line:#e5e7eb; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans"; background: var(--bg); color: var(--fg); }
    .wrap { max-width: 1200px; margin: 24px auto; padding: 0 16px; }
    h1 { font-size: 22px; margin: 0 0 16px; }
    .card { background:#fff; border:1px solid var(--line); border-radius: 14px; box-shadow: 0 2px 10px rgba(2,8,23,.04); padding:16px; }
    .row { display:flex; gap:12px; flex-wrap: wrap; }
    .field { display:flex; flex-direction: column; gap:6px; min-width: 240px; }
    label { font-size: 12px; color: var(--muted); }
    input, select, textarea { border:1px solid var(--line); border-radius: 10px; padding:10px 12px; font-size:14px; background:#fff; }
    textarea { min-height: 92px; width: 100%; }
    input[type="checkbox"] { width:auto; scale:1.1; }
    button { border:1px solid var(--prim); background: var(--prim); color:#fff; padding:10px 14px; border-radius: 12px; font-weight:600; cursor:pointer; }
    button.secondary { background:#fff; color: var(--prim); }
    button.ghost { background:#fff; color: var(--fg); border-color: var(--line); }
    button:disabled { opacity:.6; cursor:not-allowed; }
    .actions { display:flex; gap:10px; align-items:center; flex-wrap: wrap; }
    .status { font-size:12px; color: var(--muted); }
    table { width:100%; border-collapse: collapse; }
    thead th { position: sticky; top:0; background:#f1f5f9; z-index:1; }
    th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align: top; }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; border:1px solid #e2e8f0; background:#f8fafc; }
    .grid { display:grid; grid-template-columns: 1fr; gap:16px; }
    @media (min-width: 1024px) { .grid { grid-template-columns: 1fr 1fr; } }
    pre { white-space: pre-wrap; word-break: break-word; background:#0b1220; color:#e2e8f0; padding:12px; border-radius: 12px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    .muted { color: var(--muted); }
    .winner { border-left: 4px solid var(--ok); padding-left: 12px; }
    .error { color: var(--err); }
    .search { margin-left:auto; display:flex; gap:8px; align-items:center; }
    .scorebar { height: 6px; border-radius: 999px; background: #e2e8f0; position:relative; }
    .scorebar > span { position:absolute; top:0; left:0; height:100%; border-radius:999px; }
    .badge { display:inline-block; padding:2px 8px; border-radius: 10px; border:1px solid var(--line); font-size:12px; }
    .flexcol { display:flex; flex-direction: column; gap:6px; }
    .nowrap { white-space:nowrap; }
    /* --- collapsible cells --- */
    details.collapsible { display:block; }
    details.collapsible > summary {
      cursor: pointer;
      list-style: none;
      user-select: none;
      font-size: 12px; color: var(--muted);
      margin-bottom: 6px;
    }
    details.collapsible > summary::-webkit-details-marker { display:none; }
    .collapsed-preview {
      font-size: 13px;
      line-height: 1.35;
      max-height: 3.2em; /* ~2 строки */
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }
    details.collapsible[open] .collapsed-preview { display:none; }
    
    /* Полное содержимое внутри details */
    .full-content {
      border:1px dashed var(--line);
      border-radius: 8px;
      padding: 8px;
      font-size: 13px;
      background:#f8fafc;
      max-height: 40vh;
      overflow: auto;
      white-space: pre-wrap;       /* сохраняет переносы, но не ломает макет */
      word-break: break-word;
    }
    
    /* --- raw LLM answer --- */
    #raw {
      white-space: pre;            /* ничего не сворачиваем автоматически */
      word-break: normal;          /* без принудительного переноса слов */
      overflow: auto;              /* горизонтальная/вертикальная прокрутка */
      max-height: 50vh;            /* чтобы карточка не растягивала страницу бесконечно */
    }
    .raw-actions {
      display:flex; gap:8px; align-items:center; margin-bottom:8px;
    }

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
          <input id="limit" type="number" min="1" step="1" value="200" />
        </div>
        <div class="field" style="min-width:320px; flex:1">
          <label>Критерии оценивания (передаются в LLM)</label>
          <textarea id="criteria">- Насколько интересен и полезен вопрос для широкой аудитории;
- Сколько актуальных тем он затрагивает и насколько глубоко;
- Ясность формулировки и конкретика;
- Новизна по сравнению с типичными вопросами.</textarea>
        </div>
        <div class="field" style="min-width:220px">
          <label>Опции</label>
          <div style="display:flex; gap:16px; align-items:center; padding-top:8px">
            <label class="mono"><input id="final_select" type="checkbox" checked /> do_final_llm_selection</label>
            <label class="mono"><input id="use_prescoring" type="checkbox" /> use_prescoring</label>
            <label class="mono"><input id="dedupe" type="checkbox" /> dedupe</label>
          </div>
        </div>
      </div>
      <div class="actions" style="margin-top:12px">
        <button id="btnOnlyList" class="ghost">Только кандидаты (без LLM)</button>
        <button id="btnScoreOnly" class="secondary">Оценить (LLM), без финального выбора</button>
        <button id="btnPickBest">Оценить + выбрать победителя</button>
        <span id="status" class="status"></span>
        <div class="search">
          <select id="sort">
            <option value="as_is">Порядок из бэка</option>
            <option value="score_desc">Score ↓</option>
            <option value="score_asc">Score ↑</option>
            <option value="time_asc">Время ↑</option>
            <option value="time_desc">Время ↓</option>
          </select>
          <input id="search" type="text" placeholder="поиск по вопрос/ответ/обоснование…" />
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
      <div class="raw-actions">
        <button id="rawCopy" class="ghost">Копировать</button>
        <label class="mono"><input id="rawWrap" type="checkbox" /> переносить длинные строки</label>
      </div>
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
              <th class="nowrap">#</th>
              <th class="nowrap">Score</th>
              <th>msg_id</th>
              <th>chat_id</th>
              <th class="nowrap">time (UTC)</th>
              <th>question</th>
              <th>answer</th>
              <th>reason</th>
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
    $('#btnOnlyList').disabled = b;
    $('#btnScoreOnly').disabled = b;
    $('#btnPickBest').disabled = b;
    $('#status').textContent = b ? 'выполняю…' : '';
  }
  function escapeHtml(s){ return String(s||'').replace(/[&<>\\\"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\\"":"&quot;"}[c])); }
    function truncateMiddle(s, max=160){
      if (!s) return '';
      const str = String(s);
      if (str.length <= max) return str;
      const head = Math.floor(max*0.65);
      const tail = Math.floor(max*0.25);
      return str.slice(0, head) + '…' + str.slice(-tail);
    }
    
    function renderCollapsibleCell(text, label="раскрыть"){
      const raw = String(text ?? '');
      const preview = truncateMiddle(raw.replace(/\s+/g,' ').trim(), 220);
      return `
        <details class="collapsible">
          <summary>${label}</summary>
          <div class="collapsed-preview">${escapeHtml(preview || '—')}</div>
          <pre class="full-content mono">${escapeHtml(raw || '—')}</pre>
        </details>
      `;
    }

  function scoreColor(v){
    if (v == null || isNaN(v)) return '#94a3b8';
    if (v >= 80) return '#16a34a';
    if (v >= 60) return '#22c55e';
    if (v >= 40) return '#eab308';
    if (v >= 20) return '#f97316';
    return '#dc2626';
  }

  function renderScoreCell(v){
    const val = (v==null || isNaN(v)) ? '—' : String(v);
    const pct = (v==null || isNaN(v)) ? 0 : Math.max(0, Math.min(100, v));
    const color = scoreColor(v);
    return `
      <div class="flexcol">
        <div class="badge mono" style="border-color:${color}; color:${color}">${val}</div>
        <div class="scorebar" title="${val}">
          <span style="width:${pct}%; background:${color}"></span>
        </div>
      </div>
    `;
  }

  let lastResponse = null;

  function renderTable(res){
    const tbody = $('#table tbody');
    tbody.innerHTML = '';
    const q = ($('#search').value||'').toLowerCase();
    let rows = (res?.candidates||[]).slice();

    // сортировка
    const sort = $('#sort').value;
    if (sort === 'score_desc') rows.sort((a,b)=> (b.model_score??-1) - (a.model_score??-1));
    if (sort === 'score_asc')  rows.sort((a,b)=> (a.model_score?? 1e9) - (b.model_score??1e9));
    if (sort === 'time_asc')   rows.sort((a,b)=> (a.created_at_iso||'').localeCompare(b.created_at_iso||''));
    if (sort === 'time_desc')  rows.sort((a,b)=> (b.created_at_iso||'').localeCompare(a.created_at_iso||''));

    rows.forEach(c => {
      const hay = `${c.msg_id} ${c.chat_id} ${c.content||''} ${c.answer||''} ${c.model_reason||''}`.toLowerCase();
      if (q && !hay.includes(q)) return;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="mono nowrap">${c.rank}</td>
        <td style="min-width:110px">${renderScoreCell(c.model_score)}</td>
        <td class="mono">${escapeHtml(c.msg_id)}</td>
        <td class="mono">${escapeHtml(c.chat_id)}</td>
        <td class="mono nowrap">${escapeHtml(c.created_at_iso)}</td>
        <td>${escapeHtml(c.content||'')}</td>
        <td>${renderCollapsibleCell(c.answer, "ответ — показать/скрыть")}</td>
        <td>${renderCollapsibleCell(c.model_reason, "обоснование — показать/скрыть")}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function render(res){
    lastResponse = res;

    const total = (res?.candidates_count ?? 0);
    const scored = (res?.candidates||[]).filter(x => typeof x.model_score === 'number').length;
    const avg = (scored>0)
      ? Math.round(10 * (res.candidates.filter(x => typeof x.model_score==='number').reduce((s,x)=>s+x.model_score,0)/scored)) / 10
      : null;

    $('#cnt').textContent = total;
    const s = [];
    s.push(`Кандидатов: ${total}`);
    s.push(`Оценено: ${scored}${avg!=null?` (avg: ${avg})`:''}`);
    if (res?.winner_msg_id) s.push(`Победитель: ${res.winner_msg_id}`);
    $('#summary').textContent = s.join(' · ');

    if (res?.winner_msg_id) {
      $('#winner').style.display = '';
      $('#winner').innerHTML = `<div class="mono">msg_id: <b>${escapeHtml(res.winner_msg_id)}</b></div>
                                 <div style="margin:6px 0 8px 0"><b>${escapeHtml(res.winner_content||'')}</b></div>
                                 <div class="muted">Причина: ${escapeHtml(res.model_reason||'—')}</div>`;
    } else { $('#winner').style.display='none'; $('#winner').innerHTML=''; }

    $('#raw').textContent = res?.raw_model_output || '';
    renderTable(res);
  }

  async function call(mode){
    // mode: 'onlyList' | 'scoreOnly' | 'scoreAndPick'
    try {
      uiBusy(true);
      const payload = {
        start: $('#start').value.replace('T',' '),
        end: $('#end').value.replace('T',' '),
        tz: $('#tz').value || 'Europe/Amsterdam',
        candidate_limit: Math.max(1, parseInt($('#limit').value||'200',10)),
        use_prescoring: $('#use_prescoring').checked,
        dedupe: $('#dedupe').checked,
        scoring_criteria: $('#criteria').value,
        do_final_llm_selection: (mode === 'scoreAndPick'),
        return_candidates_only: (mode === 'onlyList')
      };
      const r = await fetch('/api/pick_best_question', {
        method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      render(await r.json());
    } catch (e) {
      $('#summary').innerHTML = `<span class="error">Ошибка: ${escapeHtml(e.message||String(e))}</span>`;
      $('#raw').textContent = '';
    } finally { uiBusy(false); }
  }

  $('#btnOnlyList').addEventListener('click', ()=> call('onlyList'));
  $('#btnScoreOnly').addEventListener('click', ()=> call('scoreOnly'));
  $('#btnPickBest').addEventListener('click', ()=> call('scoreAndPick'));
  $('#search').addEventListener('input', ()=>{ if (lastResponse) renderTable(lastResponse); });
  $('#sort').addEventListener('change', ()=>{ if (lastResponse) renderTable(lastResponse); });
  $('#rawCopy').addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText($('#raw').textContent || '');
        $('#rawCopy').textContent = 'Скопировано';
        setTimeout(()=> $('#rawCopy').textContent = 'Копировать', 1200);
      } catch {
        $('#rawCopy').textContent = 'Ошибка копирования';
        setTimeout(()=> $('#rawCopy').textContent = 'Копировать', 1200);
      }
    });
    
    $('#rawWrap').addEventListener('change', (e)=>{
      const pre = $('#raw');
      if (e.target.checked){
        pre.style.whiteSpace = 'pre-wrap';
        pre.style.wordBreak = 'break-word';
      } else {
        pre.style.whiteSpace = 'pre';
        pre.style.wordBreak = 'normal';
      }
    });

</script>
</body>
</html>
"""


# --- Routes ---
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
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON body: {e}")
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    mode = (
        "onlyList" if payload.get("return_candidates_only")
        else ("scoreAndPick" if payload.get("do_final_llm_selection") else "scoreOnly")
    )
    url = f"{BACKEND_URL.rstrip('/')}/pick_best_question"
    logger.info(f"Forwarding to backend [{mode}] -> {url}")

    timeout = httpx.Timeout(30.0, read=120.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload)
            logger.info(f"Backend status: {resp.status_code} [{mode}]")
            logger.debug(f"Backend headers: {resp.headers}")
            logger.debug(f"Backend body (truncated): {resp.text[:500]}")
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "application/json"),
            )
        except httpx.RequestError as e:
            logger.error(f"Backend unreachable: {e}")
            return JSONResponse({"error": f"backend unreachable: {str(e)}"}, status_code=502)
        except Exception as e:
            logger.exception("Unexpected error during proxy call")
            return JSONResponse({"error": f"unexpected error: {str(e)}"}, status_code=500)
