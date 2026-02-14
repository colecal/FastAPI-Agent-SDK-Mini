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

async function runAgent() {
  const text = $('#input').value.trim();
  if (!text) return;

  addMessage('user', text);
  $('#input').value = '';

  addMessage('assistant', 'Running...');
  const assistantMsg = $('#messages').lastChild.querySelector('pre');

  try {
    const resp = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: [], max_steps: 6 })
    });
    if (!resp.ok) throw new Error(await resp.text());

    const data = await resp.json();
    $('#runId').textContent = data.run_id;

    assistantMsg.textContent = data.final;

    const t = await fetch(`/api/trace/${data.run_id}`);
    if (t.ok) {
      const trace = await t.json();
      renderTrace(trace);
    }
  } catch (e) {
    assistantMsg.textContent = `Error: ${e}`;
  }
}

$('#send').addEventListener('click', runAgent);
$('#input').addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') runAgent();
});

// Initial examples
addMessage('assistant', "Try: 'calculate 2*(3+4)' or 'explain agent sdk' or 'summarize: ...'");
