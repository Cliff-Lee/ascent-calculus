const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
let traceData = null;
let traceFrames = [];
let traceIndex = 0;

function setTab(name) {
  $$('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  $$('.panel').forEach(p => p.classList.toggle('active', p.id === `panel-${name}`));
}
$$('.tab').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
$$('[data-panel]').forEach(b => b.addEventListener('click', () => setTab(b.dataset.panel)));

function statusClass(label) {
  if (label === 'proved') return 'proved';
  if (label === 'verified') return 'verified';
  if (label === 'counterexample') return 'counterexample';
  return 'open';
}
function statusText(claim) {
  if (claim.label === 'verified') return `VERIFIED THROUGH n=${claim.verified_through ?? '?'}`;
  if (claim.label === 'counterexample') return 'COUNTEREXAMPLE FOUND';
  return claim.label.toUpperCase();
}
async function api(path, body=null) {
  const opts = body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {};
  const r = await fetch(path, opts);
  const j = await r.json();
  if (!r.ok) throw new Error(j.detail || j.error || `HTTP ${r.status}`);
  return j;
}

function metric(label, value) { return `<span class="metric">${label}<strong>${value}</strong></span>`; }
function tokenHtml(p, mini=false, classes='') {
  const cls = mini ? 'minitoken' : 'token';
  if (mini) return `<div class="${cls} ${classes}" style="--v:${p.value}"><div>${p.value}</div><div class="id">id ${p.position_id}</div></div>`;
  const badges=[];
  if (p.first) badges.push('<span class="badge first">F</span>');
  if (p.asc_top) badges.push('<span class="badge top">AT</span>');
  if (p.run_start) badges.push('<span class="badge run">RS</span>');
  if (p.defect_first_not_top) badges.push('<span class="badge defect">Dᶠ</span>');
  if (p.defect_top_not_first) badges.push('<span class="badge defect">Dᵗ</span>');
  return `<button class="${cls}" data-pos="${p.position}" style="--v:${p.value}">
    <div class="value">${p.value}</div><div class="meta">pos ${p.position} · id ${p.position_id}</div><div class="badges">${badges.join('')}</div>
  </button>`;
}

function renderInspection(data, rootPrefix='') {
  if (!rootPrefix) {
    $('#inspect-summary').innerHTML = [
      metric('length', data.length), metric('height', data.height), metric('modified', data.is_modified ? 'yes' : 'no'),
      metric('avoid 2122', data.avoids_2122 ? 'yes' : 'no'), metric('avoid 2212', data.avoids_2212 ? 'yes' : 'no'),
      metric('defect size', data.defect.size), metric('P(x)', data.potential)
    ].join('');
    $('#word-strip').innerHTML = data.positions.map(p => tokenHtml(p)).join('');
    $$('#word-strip .token').forEach(el => el.addEventListener('click', () => explainPosition(data, Number(el.dataset.pos), el)));
    if (data.positions.length) explainPosition(data, data.positions[0].position, $('#word-strip .token'));
    $('#fibre-table').innerHTML = `<table><thead><tr><th>value</th><th>fibre</th><th>orientation</th><th>lower gaps</th></tr></thead><tbody>` +
      data.fibres.map(f => `<tr><td><strong>${f.value}</strong></td><td>${f.fibre.join(', ')}</td><td><span class="orientation ${f.orientation}">${f.orientation}</span></td><td>${f.gaps.filter(g=>g.lower_positions.length).map(g=>`${g.gap}: [${g.lower_positions.join(',')}]`).join(' · ') || 'none'}</td></tr>`).join('') + `</tbody></table>`;
  }
}
function explainPosition(data, pos, el) {
  $$('#word-strip .token').forEach(x=>x.classList.remove('selected'));
  if (el) el.classList.add('selected');
  const p = data.positions.find(x=>x.position===pos);
  $('#position-explanation').innerHTML = `<div class="summary-row">${metric('position',p.position)}${metric('value',p.value)}${metric('occurrence',p.occurrence_rank)}${metric('stable id',p.position_id)}</div><ul class="reason-list">${p.reasons.map(r=>`<li>${r}</li>`).join('')}</ul>`;
}
async function runInspect() {
  $('#word-strip').innerHTML='<div class="loading">Asking AC-Engine…</div>';
  try { renderInspection(await api('/api/inspect',{word:$('#inspect-word').value})); }
  catch(e){ $('#word-strip').innerHTML=`<div class="error-box">${e.message}</div>`; }
}
$('#inspect-run').addEventListener('click', runInspect);
$('#inspect-sample').addEventListener('change', e => { $('#inspect-word').value=e.target.value; runInspect(); });

function miniWord(inspect, rule=null, which='before') {
  const f=rule?.pair?.f, q=rule?.pair?.q, s=rule?.interval?.start, end=rule?.interval?.end;
  return `<div class="miniword">${inspect.positions.map(p=>{
    let cls='';
    if (which==='before' && rule && p.position>=s && p.position<f) cls+=' mark-a';
    if (which==='before' && rule && p.position>=f && p.position<q) cls+=' mark-b';
    if (p.defect_first_not_top || p.defect_top_not_first) cls+=' mark-defect';
    return tokenHtml(p,true,cls);
  }).join('')}</div>`;
}
function buildTraceFrames(data) {
  const frames=[];
  frames.push({kind:'gap', title:'ExtremeGapSwap result', before:data.source.inspection, after:data.gap_swap.output.inspection, detail:data.gap_swap.proof_trace});
  data.repair.steps.forEach(s => frames.push({kind:'repair', title:`Canonical repair ${s.index}`, before:s.before.inspection, after:s.after.inspection, detail:s}));
  if (!data.repair.steps.length) frames.push({kind:'done', title:'No repair required', before:data.gap_swap.output.inspection, after:data.repair.output?.inspection || data.gap_swap.output.inspection, detail:null});
  return frames;
}
function renderTraceFrame() {
  if (!traceFrames.length) return;
  const f=traceFrames[traceIndex];
  $('#trace-step-label').textContent=`${traceIndex+1} / ${traceFrames.length} · ${f.title}`;
  $('#trace-prev').disabled=traceIndex===0; $('#trace-next').disabled=traceIndex===traceFrames.length-1;
  $('#trace-stage').innerHTML=`<div class="trace-box"><h3>Before · ${f.before.word}</h3>${miniWord(f.before,f.kind==='repair'?f.detail:null,'before')}</div><div class="arrow">→</div><div class="trace-box"><h3>After · ${f.after.word}</h3>${miniWord(f.after,f.kind==='repair'?f.detail:null,'after')}</div>`;
  if (f.kind==='repair') {
    const d=f.detail, c=d.certificate;
    $('#trace-details').innerHTML = [
      ['Defect pair',`f=${d.pair.f}, q=${d.pair.q}, v=${d.pair.value}`],
      ['Blocks',`A=[${d.block_a.join(' ')}], B=[${d.block_b.join(' ')}]`],
      ['Potential',`${d.potential_before} → ${d.potential_after}`],
      ['Heavy crossings', d.heavy_crossing_values.length ? d.heavy_crossing_values.join(', ') : 'none'],
      ['AT identity exchange', c.ascent_top_ids_exchange_exactly ? 'exact q → f' : 'failed'],
      ['New defect values', c.newly_created_defect_values.length ? c.newly_created_defect_values.join(', ') : 'none'],
      ['Admissibility before', Object.values(d.before.defect_admissibility).every(Boolean) ? 'passes' : 'not all conditions'],
      ['Target avoidance after', d.after.inspection.avoids_2212 ? 'yes' : 'NO'],
    ].map(([a,b])=>`<div class="detail-box"><div class="label">${a}</div><div class="big">${b}</div></div>`).join('');
  } else if (f.kind==='gap' && f.detail) {
    const d=f.detail;
    $('#trace-details').innerHTML = [
      ['Gap-swap pivots',d.steps.map(s=>s.pivot).join(', ') || 'none'],
      ['Source right-oriented',d.source_right_oriented?'yes':'no'],
      ['Output left-oriented',d.output_left_oriented?'yes':'not yet'],
      ['Target pattern clean',d.pattern_target_clean?'yes':'no'],
    ].map(([a,b])=>`<div class="detail-box"><div class="label">${a}</div><div class="big">${b}</div></div>`).join('');
  } else $('#trace-details').innerHTML='';
}
async function runTrace() {
  $('#trace-stage').innerHTML='<div class="loading">Building trace from AC-Engine…</div>';
  try {
    traceData=await api('/api/trace',{word:$('#trace-word').value,left_repeats:2,right_repeats:1});
    traceFrames=buildTraceFrames(traceData); traceIndex=0; renderTraceFrame();
  } catch(e) { $('#trace-stage').innerHTML=`<div class="error-box">${e.message}</div>`; }
}
$('#trace-run').addEventListener('click',runTrace);
$('#trace-sample').addEventListener('change',e=>{ $('#trace-word').value=e.target.value; runTrace(); });
$('#trace-prev').addEventListener('click',()=>{ if(traceIndex>0){traceIndex--;renderTraceFrame();}});
$('#trace-next').addEventListener('click',()=>{ if(traceIndex<traceFrames.length-1){traceIndex++;renderTraceFrame();}});

function renderLab(r) {
  const label={label:r.label, verified_through:r.completed_through};
  const failure=r.first_failure;
  $('#lab-result').innerHTML=`<div class="card"><div class="result-head"><span class="status-chip ${statusClass(r.label)}">${statusText(label)}</span><strong>${r.transformation}</strong><span class="muted">${r.source} → ${r.target}</span></div>
  <table><thead><tr><th>n</th><th>source</th><th>target</th><th>unique images</th><th>outside</th><th>collisions</th><th>result</th></tr></thead><tbody>
  ${r.rows.map(x=>`<tr><td>${x.n}</td><td>${x.source_count}</td><td>${x.target_count}</td><td>${x.unique_images}</td><td>${x.outside_target}</td><td>${x.collisions}</td><td>${x.bijection_at_n?'✓':'✗'}</td></tr>`).join('')}</tbody></table>
  ${failure?`<div class="callout warning"><strong>Witness.</strong> ${failure.kind}${failure.source?` · source <code>${failure.source}</code>`:''}${failure.output?` → <code>${failure.output}</code>`:''}</div>`:''}
  <p class="muted small">${r.notice}</p></div>`;
}
$('#lab-run').addEventListener('click', async()=>{
  $('#lab-result').innerHTML='<div class="loading">Running finite search…</div>';
  try { renderLab(await api('/api/check',{source:$('#lab-source').value,target:$('#lab-target').value,transform:$('#lab-transform').value,max_n:Number($('#lab-maxn').value)})); }
  catch(e){ $('#lab-result').innerHTML=`<div class="error-box">${e.message}</div>`; }
});

function renderStatus(data) {
  const overall=data.status.overall;
  $('#overall-status').className=`status-chip ${statusClass(overall.label)}`;
  $('#overall-status').textContent=statusText(overall);
  $('#overall-detail').textContent=overall.detail;
  $('#claim-list').innerHTML=data.status.claims.map(c=>`<article class="claim"><span class="status-chip ${statusClass(c.label)}">${statusText(c)}</span><h3>${c.title}</h3><p>${c.detail}</p>${c.witness?`<p><code>${c.witness}</code></p>`:''}</article>`).join('');
  $('#contract-tasks').innerHTML=data.contract.tasks.map(x=>`<li>${x}</li>`).join('');
  $('#contract-rule').textContent=data.contract.rule;
}

async function boot() {
  try {
    const data=await api('/api/status'); renderStatus(data); $('#connection-state').textContent='Connected to AC-Engine';
    await runInspect(); await runTrace();
  } catch(e) {
    $('#connection-state').textContent='Engine unavailable';
    $('#overall-detail').textContent='Start the local GUI-1 server to use the interactive prototype.';
  }
}
boot();
