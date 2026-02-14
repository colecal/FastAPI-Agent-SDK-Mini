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
    const resp = await fetch('./api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: [], max_steps: 6 })
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

// Initial examples
addMessage('assistant', "Try: 'calculate 2*(3+4)' or 'explain agent sdk' or 'summarize: ...'");
