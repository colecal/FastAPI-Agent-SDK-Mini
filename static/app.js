const $ = (sel) => document.querySelector(sel);

function addMessage(role, content) {
  const wrap = document.createElement('div');
  wrap.className = `msg ${role}`;
  wrap.innerHTML = `<div class="role">${role}</div><pre></pre>`;
  wrap.querySelector('pre').textContent = content;
  $('#messages').appendChild(wrap);
  $('#messages').scrollTop = $('#messages').scrollHeight;
}

function renderTrace(trace) {
  const el = $('#trace');
  el.innerHTML = '';

  if (!trace || !trace.steps || trace.steps.length === 0) {
    el.innerHTML = '<div class="empty">No steps captured.</div>';
    return;
  }

  trace.steps.forEach((s) => {
    const step = document.createElement('div');
    step.className = 'step';

    const tool = s.tool_call ? `${s.tool_call.tool_name}(${JSON.stringify(s.tool_call.arguments)})` : '(none)';
    const toolResult = s.tool_result ? JSON.stringify(s.tool_result, null, 2) : '';

    step.innerHTML = `
      <div class="k">Step ${s.step} • ${(s.ended_at_ms - s.started_at_ms)} ms</div>
      <div class="k">Plan</div>
      <div class="v">${escapeHtml(s.plan)}</div>
      <div class="k">Tool</div>
      <div class="v">${escapeHtml(tool)}</div>
      <div class="k">Observation</div>
      <div class="v">${escapeHtml(s.observation || '')}</div>
      <div class="k">Tool result</div>
      <div class="v">${escapeHtml(toolResult)}</div>
    `;

    el.appendChild(step);
  });
}

function escapeHtml(str) {
  return (str || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function safeCalc(expr){
  const cleaned = String(expr || '').replace(/[^0-9\+\-\*\/\(\)\.\s%]/g,'');
  // extremely small demo: uses Function; OK for mock demo only.
  return Function(`"use strict"; return (${cleaned})`)();
}

function summarizeText(text, n){
  const parts = String(text || '').replace(/\n/g,' ').split('.').map(s=>s.trim()).filter(Boolean);
  let out = parts.slice(0, n).join('. ');
  if(out && !out.endsWith('.')) out += '.';
  return out;
}

function mockRun(text){
  const msg = String(text || '');
  const lower = msg.toLowerCase().trim();

  const steps = [];
  let final = '';

  const t0 = performance.now();

  const pushStep = (s) => steps.push({
    ...s,
    started_at_ms: Math.round(performance.now()),
    ended_at_ms: Math.round(performance.now() + 1)
  });

  if(lower.includes('calculate') || /[0-9][\d\s\+\-\*\/\(\)\.]/.test(lower)){
    const expr = lower.includes('calculate') ? msg.split(/calculate/i)[1].trim() : msg;
    let result;
    try { result = safeCalc(expr); }
    catch(e){ result = String(e); }

    pushStep({
      step: 1,
      plan: 'Use calculator tool to evaluate the expression.',
      tool_call: { tool_name: 'calculator', arguments: { expression: expr } },
      tool_result: result,
      observation: `Result: ${result}`
    });

    final = `Result: ${result}`;
  } else if(lower.startsWith('summarize') || lower.includes('summary')){
    const payload = msg.includes(':') ? msg.split(':',2)[1].trim() : msg;
    const result = summarizeText(payload, 3);

    pushStep({
      step: 1,
      plan: 'Use summarize_text tool to summarize the text.',
      tool_call: { tool_name: 'summarize_text', arguments: { text: payload, max_sentences: 3 } },
      tool_result: result,
      observation: result
    });

    final = result;
  } else {
    pushStep({
      step: 1,
      plan: 'No tool needed in mock mode.',
      tool_call: null,
      tool_result: null,
      observation: "Mock mode: try 'calculate 2*(3+4)' or 'summarize: ...'"
    });
    final = steps[0].observation;
  }

  const run_id = `mock-${Date.now()}`;
  const trace = { run_id, steps, total_ms: Math.round(performance.now() - t0) };
  return { run_id, final, trace };
}

function shouldForceMock(){
  const params = new URLSearchParams(location.search);
  if(params.get('mock') === '1') return true;
  // GitHub Pages: no backend, so default to mock.
  if(location.hostname.endsWith('github.io')) return true;
  return false;
}

function loadApiKey(){
  try { return localStorage.getItem('FASTAPI_AGENT_SDK_API_KEY') || ''; }
  catch(e){ return ''; }
}

function saveApiKey(v){
  try {
    if(!v) localStorage.removeItem('FASTAPI_AGENT_SDK_API_KEY');
    else localStorage.setItem('FASTAPI_AGENT_SDK_API_KEY', v);
  } catch(e){}
}

async function fetchTools(){
  const el = $('#tools');
  if(!el) return;

  // Pages demo: no backend
  if(shouldForceMock()){
    el.innerHTML = `
      <div class="toolCard">
        <div class="name">calculator</div>
        <div class="desc">Evaluate a math expression (demo-safe).</div>
        <div class="toolMeta">
          <span class="toolPill">mock</span>
          <span class="toolPill">allowed</span>
        </div>
      </div>
      <div class="toolCard">
        <div class="name">summarize_text</div>
        <div class="desc">Summarize text into a few sentences.</div>
        <div class="toolMeta">
          <span class="toolPill">mock</span>
          <span class="toolPill">allowed</span>
        </div>
      </div>
    `;
    return;
  }

  el.innerHTML = '<div class="empty">Loading tools…</div>';
  try{
    const r = await fetch('./api/tools');
    if(!r.ok) throw new Error(await r.text());
    const data = await r.json();
    const tools = data.tools || [];

    if(!tools.length){
      el.innerHTML = '<div class="empty">No tools registered.</div>';
      return;
    }

    el.innerHTML = '';
    tools.forEach((t)=>{
      const card = document.createElement('div');
      card.className = 'toolCard';
      const allowed = t.permission?.allow !== false;
      card.innerHTML = `
        <div class="name">${escapeHtml(t.name)}</div>
        <div class="desc">${escapeHtml(t.description || '')}</div>
        <div class="toolMeta">
          <span class="toolPill">${allowed ? 'allowed' : 'denied'}</span>
          <span class="toolPill">${escapeHtml(JSON.stringify(Object.keys(t.input_schema||{})).slice(0,60))}</span>
        </div>
      `;
      el.appendChild(card);
    });
  }catch(e){
    el.innerHTML = `<div class="empty">Couldn’t load tools from backend. (${escapeHtml(String(e))})</div>`;
  }
}

async function runAgent() {
  const text = $('#input').value.trim();
  if (!text) return;

  addMessage('user', text);
  $('#input').value = '';

  addMessage('assistant', 'Running...');
  const assistantMsg = $('#messages').lastChild.querySelector('pre');

  if(shouldForceMock()){
    const out = mockRun(text);
    $('#runId').textContent = out.run_id;
    assistantMsg.textContent = out.final;
    renderTrace(out.trace);
    return;
  }

  try {
    const apiKey = ($('#apiKey')?.value || '').trim();
    saveApiKey(apiKey);

    const resp = await fetch('./api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: [], max_steps: 6, api_key: apiKey || null })
    });
    if (!resp.ok) throw new Error(await resp.text());

    const data = await resp.json();
    $('#runId').textContent = data.run_id;

    assistantMsg.textContent = data.final;

    const t = await fetch(`./api/trace/${data.run_id}`);
    if (t.ok) {
      const trace = await t.json();
      renderTrace(trace);
    }
  } catch (e) {
    // fall back to mock mode if backend isn't available
    const out = mockRun(text);
    $('#runId').textContent = out.run_id;
    assistantMsg.textContent = out.final;
    renderTrace(out.trace);
  }
}

$('#send').addEventListener('click', runAgent);
$('#input').addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') runAgent();
});

// API key persistence
if($('#apiKey')){
  $('#apiKey').value = loadApiKey();
  $('#apiKey').addEventListener('change', (e)=> saveApiKey(e.target.value.trim()));
}

if($('#refreshTools')) $('#refreshTools').addEventListener('click', fetchTools);
fetchTools();

// Initial examples
addMessage('assistant', "Try: 'calculate 2*(3+4)' or 'explain agent sdk' or 'summarize: ...'");
