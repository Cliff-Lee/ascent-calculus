const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

// Short, example-led explanations for every choice in the workbench. Native
// option titles provide a fallback; the shared tooltip also works with native
// selects whose option hover UI is controlled by the operating system.
const STAT_HELP = {
  none: 'Do not compare a word statistic. Compare only how many words are in each class.',
  ascents: 'Count adjacent rises xᵢ < xᵢ₊₁. Example: 1,2,1,3,2 has 2 ascents (1→2 and 1→3).',
  ascent_runs: 'Count the engine-defined ascent runs. Example: 1,2,1,3,2 has 3 runs, starting at positions 1, 3, and 5.',
  run_start_positions: 'List positions where an ascent run starts. Example: 1,2,1,3,2 → [1,3,5].',
  run_lengths: 'List the lengths of consecutive ascent-run blocks. Example: 1,2 | 1,3 | 2 gives [2,2,1].',
  maximum: 'Return the largest value in the word. Example: max(1,2,1,3,2) = 3.',
  distinct_values: 'Count different values in the word. Example: {1,2,3} gives 3.',
  multiplicity_partition: 'Sort value frequencies from largest to smallest. Example: 1,2,1,3,2 has frequencies 2,2,1, so [2,2,1].',
  first_occurrence_positions: 'List positions where each distinct value first appears. Example: 1,2,1,3,2 → [1,2,4].',
  last_occurrence_positions: 'List positions that are the final occurrence of a value, sorted left to right. Example: 1,2,1,3,2 → [3,4,5].'
};
const OPTION_HELP = {
  'inspect-sample': {
    '133122': 'A modified-sequence example. Inspect its value fibres and position roles: 1,3,3,1,2,2.',
    '12321432': 'A source word used to illustrate the earlier one-step repair trace: 1,2,3,2,1,4,3,2.',
    '12143232': 'A counterexample showing a defect in the raw gap-swap rule: 1,2,1,4,3,2,3,2.',
    '14323312': 'A guardrail example: a locally plausible repair can fail the required target condition.'
  },
  'trace-sample': {
    '12321432': 'Successful one-step repair example. Build the trace to follow each occurrence through the move.',
    '14323312': 'Provenance guardrail example. Shows why the historical one-pass repair is not a general proof.'
  },
  'experiment-question': {
    compare: 'Build classes A and B, then compare their counts degree by degree. Example: Modified avoiding 2122 versus Modified avoiding 2212.',
    count: 'Build only class A and report its count at each degree. Use this when there is no second class to compare.'
  },
  'experiment-left-family': {
    ordinary: 'Ordinary ascent sequences: start with 1; each later xᵢ satisfies 1 ≤ xᵢ ≤ 2 + asc(x₁…xᵢ₋₁). Example: 1,2,1.',
    modified: 'Cayley words where each value first appears as an ascent top. Example: 1,3,3,1,2,2.',
    revised: 'Cayley words where each value first appears as an ascent bottom. Example: 2,1,2.'
  },
  'experiment-right-family': {
    ordinary: 'Ordinary ascent sequences: start with 1; each later xᵢ satisfies 1 ≤ xᵢ ≤ 2 + asc(x₁…xᵢ₋₁). Example: 1,2,1.',
    modified: 'Cayley words where each value first appears as an ascent top. Example: 1,3,3,1,2,2.',
    revised: 'Cayley words where each value first appears as an ascent bottom. Example: 2,1,2.'
  },
  'tx-source-family': {
    ordinary: 'Ordinary ascent sequences: start with 1 and each later value is at most 2 plus the earlier ascent count.',
    modified: 'Cayley words where every value first appears at the top of an ascent. Example: 1,3,3,1,2,2.',
    revised: 'Cayley words where every value first appears at the bottom of an ascent. Example: 2,1,2.'
  },
  'tx-target-family': {
    ordinary: 'Require each transformed output to be an ordinary ascent sequence.',
    modified: 'Require each transformed output to be a modified ascent sequence: a Cayley word with first occurrences at ascent tops.',
    revised: 'Require each transformed output to be a revised ascent sequence: a Cayley word with first occurrences at ascent bottoms.'
  },
  'experiment-left-mode': {
    avoid: 'Keep words with no occurrence of any listed pattern. Example: Avoid 2122 means no subsequence has relative-order pattern 2,1,2,2.',
    contain: 'Keep words with an occurrence of every listed pattern. With patterns 2122 and 2212, a word must contain both.',
    none: 'Ignore the pattern list; only the selected sequence family and structural filter apply.'
  },
  'experiment-right-mode': {
    avoid: 'Keep words with no occurrence of any listed pattern. Example: Avoid 2122 means no subsequence has relative-order pattern 2,1,2,2.',
    contain: 'Keep words with an occurrence of every listed pattern. With patterns 2122 and 2212, a word must contain both.',
    none: 'Ignore the pattern list; only the selected sequence family and structural filter apply.'
  },
  'tx-source-mode': {
    none: 'Use the whole selected source family.',
    avoid: 'Only transform source words that avoid the listed source pattern. Example: enter 2122 to filter out those containing it.',
    contain: 'Only transform source words containing the listed source pattern.'
  },
  'tx-target-mode': {
    none: 'Do not impose a pattern restriction on outputs; still check membership in the target family.',
    avoid: 'Require each output to avoid the listed target pattern. Example: 2212 filters outputs containing that pattern.',
    contain: 'Require each output to contain the listed target pattern.'
  },
  'experiment-statistic': STAT_HELP,
  'tx-statistic': STAT_HELP,
  'experiment-condition-stat': {
    none: 'Apply no additional statistic-based filter to either class.',
    ascents: 'Filter by the number of adjacent rises xᵢ < xᵢ₊₁. Example: 1,2,1 has 1 ascent.',
    maximum: 'Filter by the largest value. Example: max(1,2,1,3,2) = 3.',
    distinct_values: 'Filter by the number of different values. Example: 1,2,1,3,2 has 3.'
  },
  'experiment-condition-op': {
    eq: 'Keep words whose selected statistic equals the value exactly. Example: ascent count exactly 2.',
    ge: 'Keep words whose selected statistic is at least the value. Example: maximum at least 3.',
    le: 'Keep words whose selected statistic is at most the value. Example: distinct values at most 4.'
  },
  'tx-name': {
    hat: 'Hat map: compose prefix lifts at ascent-top positions. Example: 1,2,1,2 maps to 1,3,1,2.',
    inverse_hat: 'Partial inverse of the hat map. It recovers a source only when the input is in the hat map’s image.',
    prefix_lift: 'At pivot i, raise each earlier entry ≥ xᵢ by 1. Example: 2,1,2 with pivot 2 becomes 3,1,2.',
    inverse_prefix_lift: 'Undo a prefix lift when pivot i is a first occurrence. Example: 3,1,2 with pivot 2 returns to 2,1,2.',
    insert_position: 'Insert a copy of an existing value after a chosen cut. Example: 1,2,1, cut 1, value 2 → 1,2,2,1.',
    delete_position: 'Remove one chosen position while keeping ambient value levels. Example: 1,2,2,1, delete position 3, value 2 → 1,2,1.',
    reverse: 'Reverse the order of entries. Example: 1,2,3,1 → 1,3,2,1.',
    complement: 'Replace each value v by h+1−v, where h is the ambient height. Example at height 3: 1,2,3 → 3,2,1.'
  },
  'browser-stat': {
    '': 'Show all words, regardless of statistic.',
    ascents: STAT_HELP.ascents,
    ascent_runs: STAT_HELP.ascent_runs,
    run_lengths: STAT_HELP.run_lengths,
    maximum: STAT_HELP.maximum,
    distinct_values: STAT_HELP.distinct_values,
    multiplicity_partition: STAT_HELP.multiplicity_partition,
    first_occurrence_positions: STAT_HELP.first_occurrence_positions,
    last_occurrence_positions: STAT_HELP.last_occurrence_positions,
    run_start_positions: STAT_HELP.run_start_positions
  },
  'browser-pattern-mode': {
    none: 'Do not filter by pattern; keep every generated word.',
    contain: 'Keep words containing the pattern as an order-isomorphic subsequence. Example: 2122 occurs in 3,1,3,3.',
    avoid: 'Keep words with no order-isomorphic subsequence matching the pattern.'
  },
  'lab-source': {
    m2122: 'Modified ascent sequences that avoid 2122.',
    m2212: 'Modified ascent sequences that avoid 2212.',
    modified: 'All modified ascent sequences, with no pattern restriction.'
  },
  'lab-transform': {
    repair21: 'Historical one-pass GapSwapRepair(2,1); retained to reproduce earlier experiments.',
    gap21: 'Historical ExtremeGapSwap(2,1) candidate; inspect its bounded counterexamples before drawing conclusions.',
    repair12: 'Historical one-pass GapSwapRepair(1,2), with the pattern roles exchanged.',
    gap12: 'Historical ExtremeGapSwap(1,2) candidate, with the pattern roles exchanged.',
    reverse: 'Read each source word backward.',
    identity: 'Leave every source word unchanged; useful as a baseline check.'
  },
  'lab-target': {
    m2122: 'Require outputs to be modified ascent sequences avoiding 2122.',
    m2212: 'Require outputs to be modified ascent sequences avoiding 2212.',
    modified: 'Require outputs to be modified ascent sequences with no pattern restriction.'
  },
  'lab-maxn': {
    '6': 'Check degrees 1 through 6. Smaller ranges run faster; larger ranges test more cases.',
    '7': 'Check degrees 1 through 7.', '8': 'Check degrees 1 through 8.',
    '9': 'Check degrees 1 through 9.', '10': 'Check degrees 1 through 10; this can take longer.'
  }
};
const OPTION_TIP_ID = 'option-help-tooltip';
const optionTip = document.createElement('div');
optionTip.id = OPTION_TIP_ID;
optionTip.className = 'option-help-tooltip';
optionTip.setAttribute('role', 'tooltip');
optionTip.hidden = true;
document.body.append(optionTip);
function optionDescription(select, option=select.selectedOptions?.[0]) {
  if (!option) return '';
  const map = OPTION_HELP[select.id] || {};
  return map[option.value] || option.title || '';
}
function describeSelect(select, show=false) {
  if (!select || select.tagName !== 'SELECT') return;
  for (const option of select.options) {
    const description = optionDescription(select, option);
    if (description) option.title = description;
  }
  const description = optionDescription(select);
  if (description) {
    select.title = description;
    const describedBy = new Set((select.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));
    describedBy.add(OPTION_TIP_ID);
    select.setAttribute('aria-describedby', [...describedBy].join(' '));
  }
  if (show && description) showOptionTip(select, description);
}
function showOptionTip(select, description=optionDescription(select)) {
  if (!description) return;
  optionTip.textContent = description;
  optionTip.hidden = false;
  const rect = select.getBoundingClientRect();
  const width = Math.min(320, window.innerWidth - 24);
  const left = Math.max(12, Math.min(rect.left, window.innerWidth - width - 12));
  optionTip.style.width = `${width}px`;
  optionTip.style.left = `${left}px`;
  const below = rect.bottom + 8;
  const top = below + optionTip.offsetHeight <= window.innerHeight - 12 ? below : Math.max(12, rect.top - optionTip.offsetHeight - 8);
  optionTip.style.top = `${top}px`;
}
function hideOptionTip() { optionTip.hidden = true; }
$$('select').forEach(select => describeSelect(select));
document.addEventListener('pointerover', event => {
  const select = event.target.closest?.('select');
  if (select) { describeSelect(select, true); }
});
document.addEventListener('pointerout', event => {
  if (event.target.matches?.('select') && !event.target.contains(event.relatedTarget)) hideOptionTip();
});
document.addEventListener('focusin', event => {
  if (event.target.matches?.('select')) describeSelect(event.target, true);
});
document.addEventListener('focusout', event => {
  if (event.target.matches?.('select')) hideOptionTip();
});
document.addEventListener('change', event => {
  if (event.target.matches?.('select')) describeSelect(event.target, document.activeElement === event.target);
});
window.addEventListener('scroll', hideOptionTip, {passive:true});
window.addEventListener('resize', hideOptionTip, {passive:true});
$$('[data-family-chip]').forEach(button => { button.title = OPTION_HELP['experiment-left-family'][button.dataset.familyChip] || 'Drag this sequence family onto class A or B, or click to add it to the last focused class.'; });
$$('[data-mode-chip]').forEach(button => { button.title = OPTION_HELP['experiment-left-mode'][button.dataset.modeChip] || 'Drag this pattern rule onto class A or B, or click to apply it to the last focused class.'; });
$$('[data-pattern-chip]').forEach(button => { button.title = `Drag pattern ${button.dataset.patternChip} onto a class card to add it to that class’s rule list.`; });
$$('[data-experiment-preset]').forEach(button => {
  button.title = button.dataset.experimentPreset === 'modified-pattern-pair'
    ? 'Load a worked example comparing modified ascent sequences that avoid 2122 and 2212.'
    : 'Load a worked example comparing revised sequences avoiding 3121 with ordinary sequences avoiding 221.';
});
let traceData = null;
let traceFrames = [];
let traceIndex = 0;
let activeExperiment = null;
let objectBrowserState = null;
let lastFocusSide = 'left';
let researchStateReady = false;
let researchStateTimer = null;
let researchStateWrite = Promise.resolve();
let persistentSavedExperiments = null;

function setTab(name) {
  const previous = $('.panel.active');
  const selectedTool = name === 'learn' ? 'lab' : name;
  $$('.tab').forEach(b => {
    const active = b.dataset.tab === selectedTool;
    b.classList.toggle('active', active);
    b.setAttribute('aria-selected', String(active));
    b.tabIndex = active ? 0 : -1;
  });
  $$('.panel').forEach(p => {
    const active = p.id === `panel-${name}`;
    p.classList.toggle('active', active);
    p.setAttribute('aria-hidden', String(!active));
  });
  if (name === 'inspector' && !$('#word-strip').dataset.loaded) runInspect();
  if (name === 'trace' && !$('#trace-stage').dataset.loaded) runTrace();
  if (previous && previous.id !== `panel-${name}`) window.scrollTo({top:0, behavior:'smooth'});
}
const tablist = $('.sidebar-nav');
function syncTabOrientation() {
  tablist.setAttribute('aria-orientation', 'horizontal');
}
syncTabOrientation();
window.addEventListener('resize', syncTabOrientation, {passive:true});
$$('.tab').forEach((b, i, tabs) => {
  b.addEventListener('click', () => setTab(b.dataset.tab));
  b.addEventListener('keydown', e => {
    let next = null;
    const forward = tablist.getAttribute('aria-orientation') === 'vertical' ? 'ArrowDown' : 'ArrowRight';
    const backward = tablist.getAttribute('aria-orientation') === 'vertical' ? 'ArrowUp' : 'ArrowLeft';
    if (e.key === forward) next = (i + 1) % tabs.length;
    if (e.key === backward) next = (i - 1 + tabs.length) % tabs.length;
    if (e.key === 'Home') next = 0;
    if (e.key === 'End') next = tabs.length - 1;
    if (next !== null) {
      e.preventDefault();
      tabs[next].focus();
      setTab(tabs[next].dataset.tab);
    }
  });
});
$$('[data-panel]').forEach(b => b.addEventListener('click', () => setTab(b.dataset.panel)));
$$('.term[data-tip]').forEach((term, i) => {
  const id = `definition-${i + 1}`;
  const description = document.createElement('span');
  description.className = 'sr-only';
  description.id = id;
  description.textContent = term.dataset.tip;
  term.setAttribute('aria-describedby', id);
  term.append(description);
});

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

async function runResearchJob(kind, specification, rootSelector, runSelector, cancelSelector, renderResult) {
  const root=$(rootSelector), runButton=$(runSelector), cancelButton=$(cancelSelector);
  let jobId=null;
  runButton.disabled=true;
  cancelButton.hidden=false;
  cancelButton.disabled=true;
  cancelButton.textContent='Cancel run';
  cancelButton.onclick=async()=>{
    if (!jobId) return;
    cancelButton.disabled=true;
    cancelButton.textContent='Cancelling…';
    try { await api(`/api/jobs/${jobId}/cancel`,{}); }
    catch(e) { root.innerHTML=`<div class="error-box">${escapeHtml(e.message)}</div>`; }
  };
  root.innerHTML='<div class="loading card">Starting the bounded engine run…</div>';
  try {
    let job=await api('/api/jobs',{kind,specification});
    jobId=job.job_id;
    cancelButton.disabled=false;
    while (!['completed','cancelled','failed'].includes(job.status)) {
      const progress=job.progress||{};
      const detail=progress.degree
        ? `Degree n=${progress.degree} · ${formatCount(progress.degree_objects_tested||0)} checked in this pass · ${formatCount(progress.total_objects_tested||0)} checked overall · ${progress.completed_degrees||0}/${progress.total_degrees||'?'} degrees complete.`
        : `Run ${job.status}…`;
      root.innerHTML=`<div class="loading card" aria-live="polite">${escapeHtml(detail)}</div>`;
      await new Promise(resolve=>setTimeout(resolve,250));
      job=await api(`/api/jobs/${jobId}`);
    }
    if (job.status==='failed') throw new Error(job.error?.detail||'The bounded experiment failed.');
    renderResult(job.result);
  } catch(e) {
    root.innerHTML=`<div class="error-box">${escapeHtml(e.message)}</div>`;
  } finally {
    runButton.disabled=false;
    cancelButton.hidden=true;
    cancelButton.disabled=true;
    cancelButton.textContent='Cancel run';
    cancelButton.onclick=null;
  }
}

function metric(label, value) { return `<span class="metric">${label}<strong>${value}</strong></span>`; }
function tokenHtml(p, mini=false, classes='') {
  const cls = mini ? 'minitoken' : 'token';
  if (mini) return `<div class="${cls} ${classes}" style="--v:${p.value}"><div>${p.value}</div><div class="id">id ${p.position_id}</div></div>`;
  const badges=[];
  if (p.first) badges.push('<span class="badge first" title="First: earliest position where this value appears.">F</span>');
  if (p.asc_top) badges.push('<span class="badge top" title="Ascent top: position 1 by convention, or the right end of an adjacent rise.">AT</span>');
  if (p.asc_bottom) badges.push('<span class="badge bottom" title="Ascent bottom: position 1 by convention, or the left end of an adjacent rise.">AB</span>');
  if (p.run_start) badges.push('<span class="badge run" title="Run start: position 1, or a position not entered by an ascent.">RS</span>');
  if (p.defect_first_not_top) badges.push('<span class="badge defect" title="First occurrence that is not an ascent top.">Dᶠ</span>');
  if (p.defect_top_not_first) badges.push('<span class="badge defect" title="Ascent top that is not a first occurrence.">Dᵗ</span>');
  const roles = [p.first && 'first occurrence', p.asc_top && 'ascent top', p.asc_bottom && 'ascent bottom', p.run_start && 'run start'].filter(Boolean).join(', ') || 'no marked role';
  return `<button class="${cls}" data-pos="${p.position}" title="Position ${p.position}, value ${p.value}: ${roles}. Select for the full explanation." aria-label="Position ${p.position}, value ${p.value}: ${roles}." style="--v:${p.value}">
    <div class="value">${p.value}</div><div class="meta">pos ${p.position} · id ${p.position_id}</div><div class="badges">${badges.join('')}</div>
  </button>`;
}

function renderInspection(data, rootPrefix='') {
  if (!rootPrefix) {
    $('#word-strip').dataset.loaded = 'true';
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
  $('#word-strip').dataset.loaded = '';
  $('#word-strip').innerHTML='<div class="loading">Asking AC-Engine…</div>';
  try { renderInspection(await api('/api/inspect',{word:$('#inspect-word').value})); }
  catch(e){ $('#word-strip').innerHTML=`<div class="error-box">${e.message}</div>`; }
}
$('#inspect-run').addEventListener('click', runInspect);
$('#inspect-sample').addEventListener('change', e => { $('#inspect-word').value=e.target.value; runInspect(); });

function renderLearnResult(data) {
  const labels = [
    ['Ordinary ascent sequence', data.is_ascent_sequence],
    ['Modified ascent sequence', data.is_modified],
    ['Revised ascent sequence', data.is_revised],
    ['Cayley word', data.is_cayley]
  ];
  const marks = labels.map(([label, yes]) => `<span class="classification ${yes ? 'yes' : 'no'}"><i>${yes ? '✓' : '—'}</i>${label}<b>${yes ? 'Yes' : 'No'}</b></span>`).join('');
  $('#learn-result').innerHTML = `<div class="learn-result-head"><div><span class="eyebrow">ENGINE CHECK</span><strong>${data.word}</strong><span class="muted">${data.length} positions · height ${data.height}</span></div><button class="ghost" id="learn-open-inspector">Inspect positions</button></div><div class="classification-grid">${marks}</div><p class="small muted">Cayley means every value from 1 through the height appears. Modified and revised require a Cayley word plus their first-occurrence condition.</p>`;
  $('#learn-open-inspector').addEventListener('click', () => {
    $('#inspect-word').value = data.word;
    setTab('inspector');
    runInspect();
  });
}
async function checkLearnWord() {
  const result = $('#learn-result');
  result.innerHTML = '<div class="loading">Checking the definitions in AC-Engine…</div>';
  try { renderLearnResult(await api('/api/inspect', {word:$('#learn-word').value})); }
  catch(e) { result.innerHTML = `<div class="error-box">${e.message}</div>`; }
}
$('#learn-check').addEventListener('click', checkLearnWord);
$('#learn-word').addEventListener('keydown', e => { if (e.key === 'Enter') checkLearnWord(); });
$('#learn-example').addEventListener('click', () => {
  $('#learn-word').value='1, 2, 1, 3, 2';
  $('#lesson-try').scrollIntoView({behavior:'smooth', block:'center'});
  checkLearnWord();
});
$$('[data-inspect-word]').forEach(button => button.addEventListener('click', () => {
  $('#inspect-word').value=button.dataset.inspectWord;
  setTab('inspector');
  runInspect();
}));

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
  $('#trace-stage').dataset.loaded = '';
  $('#trace-stage').innerHTML='<div class="loading">Building trace from AC-Engine…</div>';
  try {
    traceData=await api('/api/trace',{word:$('#trace-word').value,left_repeats:2,right_repeats:1});
    traceFrames=buildTraceFrames(traceData); traceIndex=0; renderTraceFrame();
    $('#trace-stage').dataset.loaded = 'true';
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

const experimentPatternChecks = {left:0, right:0};
const experimentPatternState = {left:[], right:[]};
const familyLabels = {ordinary:'Ordinary ascent sequences', modified:'Modified ascent sequences', revised:'Revised ascent sequences'};
const familyDegreeLimits = {ordinary:11, modified:11, revised:7};
const experimentControls = {
  left:{family:'#experiment-left-family', mode:'#experiment-left-mode', patterns:'#experiment-left-patterns', validation:'#experiment-left-validation', offset:'#experiment-left-offset'},
  right:{family:'#experiment-right-family', mode:'#experiment-right-mode', patterns:'#experiment-right-patterns', validation:'#experiment-right-validation', offset:'#experiment-right-offset'}
};
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function patternLines(side) {
  return $(experimentControls[side].patterns).value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
}
async function validateExperimentSide(side) {
  const c=experimentControls[side], mode=$(c.mode).value, box=$(c.validation);
  const token=++experimentPatternChecks[side];
  experimentPatternState[side]=[];
  updateExperimentValidity();
  if (mode === 'none') {
    experimentPatternState[side]=[];
    $(c.patterns).hidden=true; document.querySelector(`label[for="${c.patterns.slice(1)}"]`).hidden=true;
    box.className='pattern-validation valid'; box.textContent='Unrestricted by pattern';
    updateExperimentSentence(); updateExperimentValidity(); return true;
  }
  $(c.patterns).hidden=false; document.querySelector(`label[for="${c.patterns.slice(1)}"]`).hidden=false;
  const patterns=patternLines(side);
  if (!patterns.length) {
    experimentPatternState[side]=[];
    box.className='pattern-validation invalid'; box.textContent='Enter a Cayley pattern, or choose no pattern restriction.';
    updateExperimentSentence(); updateExperimentValidity(); return false;
  }
  box.className='pattern-validation pending'; box.textContent='Checking pattern definition…';
  try {
    const checks=await Promise.all(patterns.map(pattern=>api('/api/experiment/validate-pattern',{pattern})));
    if (token !== experimentPatternChecks[side]) return false;
    experimentPatternState[side]=checks;
    box.className='pattern-validation valid';
    box.innerHTML=checks.map(x=>`<span class="pattern-pill">${escapeHtml(x.notation)}</span>`).join(' ');
    updateExperimentSentence(); updateExperimentValidity(); return true;
  } catch(e) {
    if (token !== experimentPatternChecks[side]) return false;
    experimentPatternState[side]=[];
    box.className='pattern-validation invalid'; box.textContent=e.message;
    updateExperimentSentence(); updateExperimentValidity(); return false;
  }
}
function sideSpecification(side) {
  const c=experimentControls[side], mode=$(c.mode).value;
  return {
    family:$(c.family).value,
    degree_offset:Number($(c.offset).value || 0),
    rules:mode==='none'?[]:patternLines(side).map(pattern=>({mode,pattern}))
  };
}
const draftFieldIds=['experiment-question','experiment-start','experiment-stop','experiment-left-family','experiment-left-mode','experiment-left-patterns','experiment-left-offset','experiment-right-family','experiment-right-mode','experiment-right-patterns','experiment-right-offset','experiment-statistic','experiment-condition-stat','experiment-condition-op','experiment-condition-value'];
const draftStorageKey='ascent-engine.experiment-draft.v1';
const savedStorageKey='ascent-engine.saved-experiments.v1';
function persistDraft() {
  try {
    const draft=Object.fromEntries(draftFieldIds.map(id=>[id,$(`#${id}`).value]));
    localStorage.setItem(draftStorageKey,JSON.stringify(draft));
    if (researchStateReady) scheduleResearchStateSave(draft);
  } catch(_) { /* Local persistence is an aid; the engine run remains usable without it. */ }
}
function restoreDraft() {
  try {
    const draft=JSON.parse(localStorage.getItem(draftStorageKey)||'null');
    if (!draft || typeof draft!=='object') return;
    draftFieldIds.forEach(id=>{if (typeof draft[id]==='string') $(`#${id}`).value=draft[id];});
  } catch(_) { /* Ignore an old or unavailable local draft. */ }
}
function scheduleResearchStateSave(draft=null) {
  clearTimeout(researchStateTimer);
  researchStateTimer=setTimeout(()=>{
    const current=draft||Object.fromEntries(draftFieldIds.map(id=>[id,$(`#${id}`).value]));
    const payload={draft:current,saved:savedExperiments()};
    researchStateWrite=researchStateWrite.catch(()=>{}).then(()=>api('/api/research-state',payload)).catch(()=>{});
  },350);
}
function restoreResearchState(state) {
  if (state?.draft && typeof state.draft==='object') {
    draftFieldIds.forEach(id=>{if (typeof state.draft[id]==='string') $(`#${id}`).value=state.draft[id];});
    try { localStorage.setItem(draftStorageKey,JSON.stringify(state.draft)); } catch(_) {}
  }
  if (Array.isArray(state?.saved)) {
    persistentSavedExperiments=state.saved;
    try { localStorage.setItem(savedStorageKey,JSON.stringify(state.saved)); } catch(_) {}
  }
  renderPatternLane('left'); renderPatternLane('right');
  renderSavedExperiments();
  validateExperimentSide('left'); validateExperimentSide('right');
  researchStateReady=true;
  updateExperimentValidity();
  scheduleResearchStateSave();
}
function isSandwichPattern(values) {
  if (values.length<3 || values[0]!==values[values.length-1]) return false;
  const pivot=values[0]; let left=0, right=0;
  while (left<values.length && values[left]===pivot) left++;
  while (right<values.length && values[values.length-right-1]===pivot) right++;
  const middle=values.slice(left,values.length-right);
  return middle.length===1 && middle[0]<pivot;
}
function sideDegreeLimit(side) {
  const family=$(`#experiment-${side}-family`).value;
  let limit=familyDegreeLimits[family];
  if ($(`#experiment-${side}-mode`).value!=='none') {
    for (const pattern of experimentPatternState[side]) {
      if (pattern.arity>=3 && !isSandwichPattern(pattern.values)) limit=Math.min(limit,Math.max(5,12-pattern.arity));
    }
  }
  return limit;
}
function describeSide(side) {
  const c=experimentControls[side], family=familyLabels[$(c.family).value], mode=$(c.mode).value;
  const patterns=experimentPatternState[side].map(x=>`<span class="inline-pattern">${escapeHtml(x.values.join(','))}</span>`).join(' and ');
  const restriction=mode==='none'?'with no pattern restriction':`${mode==='avoid'?'avoiding':'containing'} ${patterns || 'the listed pattern(s)'}`;
  const offset=Number($(c.offset).value || 0);
  const at=offset===0?'at degree n':`at degree n${offset>0?'+':''}${offset}`;
  return `${escapeHtml(family)} ${restriction}, ${at}`;
}
function updateExperimentSentence() {
  const question=$('#experiment-question').value, start=$('#experiment-start').value, stop=$('#experiment-stop').value;
  const left=describeSide('left');
  const right=describeSide('right');
  const comparison=question==='compare'?` <b>with</b> ${right}`:'';
  const statistic=$('#experiment-statistic').value;
  const statisticPhrase=statistic==='none'?'':`; compare distributions by <b>${escapeHtml($('#experiment-statistic').selectedOptions[0].textContent.toLowerCase())}</b>`;
  const conditionStat=$('#experiment-condition-stat').value;
  const conditionUnits={ascents:'ascents',maximum:'maximum value',distinct_values:'distinct values'};
  const condition=conditionStat==='none'?'':`; keep words with <b>${escapeHtml($('#experiment-condition-op').selectedOptions[0].textContent)} ${escapeHtml($('#experiment-condition-value').value || '0')} ${conditionUnits[conditionStat]}</b>`;
  $('#experiment-sentence').innerHTML=`<span class="sentence-label">INTERPRETED EXPERIMENT</span><p><b>${question==='compare'?'Compare':'Count'}</b> ${left}${comparison} for <b>n=${escapeHtml(start)}…${escapeHtml(stop)}</b>${statisticPhrase}${condition}.</p>`;
}
function updateExperimentValidity() {
  const compare=$('#experiment-question').value==='compare';
  const leftValid=$('#experiment-left-mode').value==='none' || experimentPatternState.left.length===patternLines('left').length && experimentPatternState.left.length>0;
  const rightValid=!compare || $('#experiment-right-mode').value==='none' || experimentPatternState.right.length===patternLines('right').length && experimentPatternState.right.length>0;
  const start=Number($('#experiment-start').value), stop=Number($('#experiment-stop').value);
  const degreeChecks=[['left',$('#experiment-left-family').value,Number($('#experiment-left-offset').value||0),sideDegreeLimit('left')]];
  if (compare) degreeChecks.push(['right',$('#experiment-right-family').value,Number($('#experiment-right-offset').value||0),sideDegreeLimit('right')]);
  const rangeValid=Number.isInteger(start)&&Number.isInteger(stop)&&start>=1&&stop>=start&&stop<=11&&degreeChecks.every(([,family,offset,limit])=>start+offset>=1&&stop+offset<=limit);
  const message=$('#experiment-validation-summary');
  const valid=leftValid&&rightValid&&rangeValid;
  $('#experiment-run').disabled=!valid;
  if (valid) message.textContent='Ready to run.';
  else if (!Number.isInteger(start)||!Number.isInteger(stop)||start<1||stop<start||stop>11) message.textContent='Choose a valid degree range (1 to 11).';
  else if (!degreeChecks.every(([,family,offset,limit])=>start+offset>=1&&stop+offset<=limit)) {
    const limited=degreeChecks.find(([,family,offset,limit])=>start+offset<1||stop+offset>limit);
    const patternLimit=limited[3]<familyDegreeLimits[limited[1]];
    message.textContent=patternLimit?`This general pattern search is currently bounded to degree ${limited[3]}; adjust the range or pattern.`:`${familyLabels[limited[1]]} are currently enumerable through degree ${limited[3]}; adjust the range or degree shift.`;
  } else message.textContent='Correct the pattern definition before running.';
  $('#experiment-right-card').hidden=!compare;
  $('#experiment-connector').hidden=!compare;
  $('#experiment-right-offset-wrap').hidden=!compare;
  const hasCondition=$('#experiment-condition-stat').value!=='none';
  $('#experiment-condition-op').disabled=!hasCondition;
  $('#experiment-condition-value').disabled=!hasCondition;
  updateExperimentSentence();
  persistDraft();
}
function applyExperimentPreset(name) {
  $('#experiment-question').value='compare';
  $('#experiment-start').value='1';
  $('#experiment-statistic').value='none';
  $('#experiment-condition-stat').value='none';
  $('#experiment-condition-op').value='eq';
  $('#experiment-condition-value').value='2';
  if (name==='revised-shift') {
    $('#experiment-left-family').value='revised'; $('#experiment-left-mode').value='avoid'; $('#experiment-left-patterns').value='3121'; $('#experiment-left-offset').value='1';
    $('#experiment-right-family').value='ordinary'; $('#experiment-right-mode').value='avoid'; $('#experiment-right-patterns').value='221'; $('#experiment-right-offset').value='0'; $('#experiment-stop').value='6';
  } else {
    $('#experiment-left-family').value='modified'; $('#experiment-left-mode').value='avoid'; $('#experiment-left-patterns').value='2122'; $('#experiment-left-offset').value='0';
    $('#experiment-right-family').value='modified'; $('#experiment-right-mode').value='avoid'; $('#experiment-right-patterns').value='2212'; $('#experiment-right-offset').value='0'; $('#experiment-stop').value='11';
  }
  renderPatternLane('left'); renderPatternLane('right');
  validateExperimentSide('left'); validateExperimentSide('right'); updateExperimentValidity();
}
$('#experiment-question').addEventListener('change',updateExperimentValidity);
for (const id of ['experiment-start','experiment-stop','experiment-left-family','experiment-right-family','experiment-left-mode','experiment-right-mode','experiment-left-offset','experiment-right-offset','experiment-statistic','experiment-condition-stat','experiment-condition-op','experiment-condition-value']) {
  $( `#${id}` ).addEventListener('input',()=>{
    if (id.endsWith('-mode')) validateExperimentSide(id.includes('left')?'left':'right');
    else updateExperimentValidity();
  });
  $( `#${id}` ).addEventListener('change',()=>{
    if (id.endsWith('-mode')) validateExperimentSide(id.includes('left')?'left':'right');
    else updateExperimentValidity();
  });
}
for (const side of ['left','right']) $(experimentControls[side].patterns).addEventListener('input',()=>{
  renderPatternLane(side);
  validateExperimentSide(side);
  persistDraft();
});
$$('.experiment-side').forEach(card=>{
  const side=card.id.includes('left')?'left':'right';
  card.addEventListener('pointerenter',()=>{lastFocusSide=side;});
  card.addEventListener('focusin',()=>{lastFocusSide=side;});
});
$$('[data-experiment-preset]').forEach(b=>b.addEventListener('click',()=>applyExperimentPreset(b.dataset.experimentPreset)));

function renderPatternLane(side, hint='Drop a pattern or text file · × removes') {
  const zone=document.querySelector(`[data-pattern-drop="${side}"]`);
  if (!zone) return;
  const patterns=$(experimentControls[side].patterns).value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  const chips=patterns.map((pattern,index)=>`<span class="rule-chip" role="listitem" draggable="true" data-rule-index="${index}"><code>${escapeHtml(pattern)}</code><button type="button" data-remove-pattern="${index}" aria-label="Remove pattern ${escapeHtml(pattern)}">×</button></span>`).join('');
  zone.innerHTML=`${chips}<span class="drop-hint">${escapeHtml(hint)}</span>`;
  zone.querySelectorAll('.rule-chip').forEach(chip=>chip.addEventListener('dragstart',event=>{
    const index=Number(chip.dataset.ruleIndex), pattern=patterns[index];
    event.dataTransfer.setData('application/x-ascent-piece',JSON.stringify({kind:'pattern',value:pattern,source:side,index}));
    event.dataTransfer.setData('text/plain',pattern);
  }));
  zone.querySelectorAll('[data-remove-pattern]').forEach(button=>button.addEventListener('click',()=>{
    const next=patterns.filter((_,index)=>index!==Number(button.dataset.removePattern));
    const input=$(experimentControls[side].patterns); input.value=next.join('\n');
    input.dispatchEvent(new Event('input',{bubbles:true}));
  }));
}
function addPatterns(side, rawPatterns) {
  const input = $(experimentControls[side].patterns);
  const existing = input.value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  const merged = [...existing];
  rawPatterns.map(String).map(x=>x.trim()).filter(Boolean).forEach(pattern=>{
    if (!merged.includes(pattern)) merged.push(pattern);
  });
  input.value = merged.join('\n');
  input.dispatchEvent(new Event('input',{bubbles:true}));
}
function dragPiece(button, payload) {
  button.addEventListener('dragstart',event=>{
    event.dataTransfer.setData('application/x-ascent-piece',JSON.stringify(payload));
    event.dataTransfer.setData('text/plain',String(payload.value));
    event.dataTransfer.effectAllowed='copy';
  });
}
$$('[data-pattern-chip]').forEach(button=>{
  dragPiece(button,{kind:'pattern',value:button.dataset.patternChip});
  button.addEventListener('click',()=>addPatterns(lastFocusSide,[button.dataset.patternChip]));
});
$$('[data-family-chip]').forEach(button=>{
  const family=button.dataset.familyChip;
  dragPiece(button,{kind:'family',value:family});
  button.addEventListener('click',()=>{
    $(`#experiment-${lastFocusSide}-family`).value=family;
    updateExperimentValidity(); persistDraft();
  });
});
$$('[data-mode-chip]').forEach(button=>{
  const mode=button.dataset.modeChip;
  dragPiece(button,{kind:'mode',value:mode});
  button.addEventListener('click',()=>{
    $(`#experiment-${lastFocusSide}-mode`).value=mode;
    validateExperimentSide(lastFocusSide); updateExperimentValidity(); persistDraft();
  });
});
function readPiece(event) {
  const encoded=event.dataTransfer.getData('application/x-ascent-piece');
  if (encoded) return JSON.parse(encoded);
  const text=(event.dataTransfer.getData('text/plain')||'').trim();
  if (/^[1-9]+$/.test(text)) return {kind:'pattern',value:text};
  return null;
}
$$('[data-family-drop]').forEach(zone=>{
  const side=zone.dataset.familyDrop;
  zone.addEventListener('dragover',event=>{event.preventDefault();zone.classList.add('drag-over');});
  zone.addEventListener('dragleave',()=>zone.classList.remove('drag-over'));
  zone.addEventListener('drop',event=>{
    event.preventDefault(); zone.classList.remove('drag-over');
    try {
      const piece=readPiece(event);
      if (piece?.kind!=='family') throw new Error('Drop an Ordinary, Modified, or Revised family here.');
      $(`#experiment-${side}-family`).value=piece.value;
      zone.textContent=`${familyLabels[piece.value]} family selected`;
      setTimeout(()=>{zone.textContent='Drop a family here';},1500);
      updateExperimentValidity(); persistDraft();
    } catch(error) { zone.textContent=error.message; setTimeout(()=>{zone.textContent='Drop a family here';},1800); }
  });
});
$$('[data-mode-drop]').forEach(zone=>{
  const side=zone.dataset.modeDrop;
  zone.addEventListener('dragover',event=>{event.preventDefault();zone.classList.add('drag-over');});
  zone.addEventListener('dragleave',()=>zone.classList.remove('drag-over'));
  zone.addEventListener('drop',event=>{
    event.preventDefault(); zone.classList.remove('drag-over');
    try {
      const piece=readPiece(event);
      if (piece?.kind!=='mode') throw new Error('Drop Avoid or Contain here.');
      $(`#experiment-${side}-mode`).value=piece.value;
      zone.textContent=`Rule set to ${piece.value}`;
      setTimeout(()=>{zone.textContent='Drop Avoid or Contain here';},1500);
      validateExperimentSide(side); updateExperimentValidity(); persistDraft();
    } catch(error) { zone.textContent=error.message; setTimeout(()=>{zone.textContent='Drop Avoid or Contain here';},1800); }
  });
});
$$('[data-pattern-drop]').forEach(zone=>{
  const side=zone.dataset.patternDrop;
  zone.addEventListener('dragover',event=>{event.preventDefault();zone.classList.add('drag-over');});
  zone.addEventListener('dragleave',()=>zone.classList.remove('drag-over'));
  zone.addEventListener('drop',async event=>{
    event.preventDefault(); zone.classList.remove('drag-over');
    try {
      let raw=[];
      if (event.dataTransfer.files.length) {
        const file=event.dataTransfer.files[0];
        if (!/\.(txt|csv|json)$/i.test(file.name)) throw new Error('Drop a .txt, .csv, or .json file of patterns.');
        const text=await file.text();
        if (/\.json$/i.test(file.name)) {
          const parsed=JSON.parse(text);
          raw=Array.isArray(parsed)?parsed:(parsed.patterns||[]);
        } else raw=text.split(/\r?\n/).map(line=>line.trim()).filter(Boolean);
      } else {
        const piece=readPiece(event);
        if (piece?.kind==='pattern') raw=[piece.value];
        else raw=(event.dataTransfer.getData('text/plain')||'').split(/\r?\n/).map(line=>line.trim()).filter(Boolean);
      }
      if (!raw.length) throw new Error('No patterns found. Use one pattern per line.');
      const patterns=raw.map(value=>Array.isArray(value)?value.join(','):String(value).trim());
      await Promise.all(patterns.map(pattern=>api('/api/experiment/validate-pattern',{pattern})));
      addPatterns(side,patterns);
      renderPatternLane(side,`Added ${patterns.length} pattern${patterns.length===1?'':'s'}`);
      setTimeout(()=>renderPatternLane(side),1800);
    } catch(error) {
      zone.querySelector('.drop-hint').textContent=error.message;
      zone.classList.add('drop-error');
      setTimeout(()=>{renderPatternLane(side);zone.classList.remove('drop-error');},2600);
    }
  });
});
for (const side of ['left','right']) renderPatternLane(side);

function applyExperimentSpecification(raw) {
  const spec=raw?.specification || raw?.result?.specification || raw;
  if (!spec || !['count','compare'].includes(spec.question) || !spec.left) throw new Error('This JSON does not contain an Ascent Engine experiment specification.');
  const loadSide=(sideName,side)=>{
    if (!side) return;
    const rules=side.rules||[];
    const modes=[...new Set(rules.map(rule=>rule.mode))];
    if (modes.length>1) throw new Error('The compact editor can load one rule mode per family. This file mixes Avoid and Contain rules.');
    if (!familyLabels[side.family] || rules.some(rule=>!['avoid','contain'].includes(rule.mode))) throw new Error(`The ${sideName==='left'?'first':'second'} class has an unsupported family or rule.`);
    $(`#experiment-${sideName}-family`).value=side.family;
    $(`#experiment-${sideName}-mode`).value=rules.length?modes[0]:'none';
    $(`#experiment-${sideName}-patterns`).value=rules.map(rule=>Array.isArray(rule.pattern)?rule.pattern.join(','):String(rule.pattern)).join('\n');
    $(`#experiment-${sideName}-offset`).value=String(side.degree_offset||0);
  };
  $('#experiment-question').value=spec.question;
  $('#experiment-start').value=String(spec.start||1);
  $('#experiment-stop').value=String(spec.stop||6);
  $('#experiment-statistic').value=spec.statistic||'none';
  $('#experiment-condition-stat').value=spec.condition?.statistic||'none';
  $('#experiment-condition-op').value=spec.condition?.operator||'eq';
  $('#experiment-condition-value').value=String(spec.condition?.value??2);
  loadSide('left',spec.left);
  loadSide('right',spec.right||{family:'modified',degree_offset:0,rules:[]});
  renderPatternLane('left'); renderPatternLane('right');
  validateExperimentSide('left'); validateExperimentSide('right'); updateExperimentValidity();
  setTab('lab');
}

function currentExperimentRequest() {
  const conditionStat=$('#experiment-condition-stat').value;
  const condition=conditionStat==='none'?null:{statistic:conditionStat,operator:$('#experiment-condition-op').value,value:Number($('#experiment-condition-value').value||0)};
  const question=$('#experiment-question').value;
  return {question,start:Number($('#experiment-start').value),stop:Number($('#experiment-stop').value),statistic:$('#experiment-statistic').value,condition,left:sideSpecification('left'),right:question==='compare'?sideSpecification('right'):null};
}
async function runExperiment(request=currentExperimentRequest()) {
  await runResearchJob('experiment',request,'#experiment-result','#experiment-run','#experiment-cancel',renderExperiment);
  updateExperimentValidity();
}

function savedExperiments() {
  if (Array.isArray(persistentSavedExperiments)) return persistentSavedExperiments;
  try { const value=JSON.parse(localStorage.getItem(savedStorageKey)||'[]'); return Array.isArray(value)?value:[]; }
  catch(_) { return []; }
}
function savedLabel(spec) {
  const side=s=>`${familyLabels[s.family]} ${s.rules?.length?s.rules.map(r=>`${r.mode} ${Array.isArray(r.pattern)?r.pattern.join(''):r.pattern}`).join(' + '):'unrestricted'}`;
  return spec.question==='count'?side(spec.left):`${side(spec.left)}  ↔  ${side(spec.right)}`;
}
function renderSavedExperiments() {
  const items=savedExperiments();
  $('#saved-experiment-count').textContent=String(items.length);
  const root=$('#saved-experiment-list');
  root.innerHTML=items.length?items.map(item=>`<div class="saved-experiment-row"><div><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.summary||'Saved')} · ${escapeHtml(new Date(item.saved_at).toLocaleString())}</small></div><div class="saved-actions"><button type="button" class="secondary" data-run-saved="${escapeHtml(item.id)}">Load and run</button><button type="button" class="text-button" data-delete-saved="${escapeHtml(item.id)}">Remove</button></div></div>`).join(''):'<p class="small muted">No saved tests yet. Save a result to keep its specification here.</p>';
  root.querySelectorAll('[data-run-saved]').forEach(button=>button.addEventListener('click',async()=>{
    const item=savedExperiments().find(x=>x.id===button.dataset.runSaved); if (!item) return;
    try { applyExperimentSpecification(item.specification); await runExperiment(item.specification); }
    catch(error) { root.insertAdjacentHTML('afterbegin',`<div class="error-box">${escapeHtml(error.message)}</div>`); }
  }));
  root.querySelectorAll('[data-delete-saved]').forEach(button=>button.addEventListener('click',()=>{
    persistentSavedExperiments=savedExperiments().filter(x=>x.id!==button.dataset.deleteSaved);
    try { localStorage.setItem(savedStorageKey,JSON.stringify(persistentSavedExperiments)); } catch(_) {}
    renderSavedExperiments();
    scheduleResearchStateSave();
  }));
}
function saveCurrentExperiment() {
  if (!activeExperiment) return;
  const items=savedExperiments(), spec=activeExperiment.specification, key=JSON.stringify(spec);
  const same=items.find(item=>JSON.stringify(item.specification)===key);
  const record={id:same?.id||`${Date.now()}-${Math.random().toString(36).slice(2,8)}`,label:savedLabel(spec),saved_at:new Date().toISOString(),specification:spec,summary:activeExperiment.headline,first_divergence:activeExperiment.first_divergence,rows:activeExperiment.rows.map(row=>({n:row.n,left:row.left_count,right:row.right_count,difference:row.difference}))};
  const next=[record,...items.filter(item=>JSON.stringify(item.specification)!==key)].slice(0,30);
  persistentSavedExperiments=next;
  try { localStorage.setItem(savedStorageKey,JSON.stringify(next)); } catch(_) {}
  renderSavedExperiments(); scheduleResearchStateSave();
  $('#saved-experiments-feedback').textContent='Saved on this device.';
}
function exportExperiment() {
  if (!activeExperiment) return;
  const blob=new Blob([JSON.stringify({format:'ascent-engine-experiment-v1',exported_at:new Date().toISOString(),result:activeExperiment},null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob), link=document.createElement('a');
  link.href=url; link.download='ascent-engine-experiment.json'; link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$('#save-experiment').addEventListener('click',saveCurrentExperiment);
$('#export-experiment').addEventListener('click',exportExperiment);
$('#import-experiment').addEventListener('change',async event=>{
  const file=event.target.files?.[0]; if (!file) return;
  try { applyExperimentSpecification(JSON.parse(await file.text())); $('#saved-experiments-feedback').textContent=`Loaded ${file.name}. Run it to check the result.`; }
  catch(error) { $('#saved-experiments-feedback').textContent=error.message; }
  finally { event.target.value=''; }
});
renderSavedExperiments();
function formatCount(value) { return Number(value).toLocaleString(); }
function distributionDetails(row, statisticLabel) {
  const left=new Map((row.left_distribution||[]).map(item=>[JSON.stringify(item.value),item.count]));
  const right=new Map((row.right_distribution||[]).map(item=>[JSON.stringify(item.value),item.count]));
  const keys=[...new Set([...left.keys(),...right.keys()])].sort((a,b)=>{
    const x=JSON.parse(a), y=JSON.parse(b), xa=Array.isArray(x)?x:[x], ya=Array.isArray(y)?y:[y];
    for (let i=0;i<Math.min(xa.length,ya.length);i++) if (xa[i]!==ya[i]) return xa[i]-ya[i];
    return xa.length-ya.length;
  });
  const rows=keys.map(key=>{
    const value=JSON.parse(key), a=left.get(key)||0, b=right.get(key)||0, difference=a-b;
    const shown=Array.isArray(value)?value.join(', '):String(value);
    return `<tr><th scope="row">${escapeHtml(shown)}</th><td>${formatCount(a)}</td><td>${formatCount(b)}</td><td class="difference ${difference===0?'zero':'nonzero'}">${difference>0?'+':''}${formatCount(difference)}</td></tr>`;
  }).join('');
  return `<section class="distribution-inspector card"><div class="browser-head"><div><span class="eyebrow">DISTRIBUTION AUTOPSY · n=${row.n}</span><h3>${escapeHtml(statisticLabel)}</h3><p class="small muted">Each row groups class members by this statistic value.</p></div><button class="icon-button" id="close-distribution" aria-label="Close distribution details">×</button></div><div class="experiment-table-wrap"><table><thead><tr><th>Statistic value</th><th>First</th><th>Second</th><th>Difference</th></tr></thead><tbody>${rows||'<tr><td colspan="4">No matching objects</td></tr>'}</tbody></table></div></section>`;
}
function formatExperimentSide(side) {
  const family=familyLabels[side.family];
  const patternText=side.rules.length?side.rules.map(rule=>`${rule.mode} <span class="inline-pattern">${rule.pattern.join(',')}</span>`).join(' and '):'unrestricted';
  const degree=side.degree_offset===0?'n':`n${side.degree_offset>0?'+':''}${side.degree_offset}`;
  return `${escapeHtml(family)} ${patternText}, degree ${escapeHtml(degree)}`;
}
function renderExperiment(result) {
  activeExperiment = result;
  $('#save-experiment').disabled=false;
  $('#export-experiment').disabled=false;
  objectBrowserState = null;
  const spec=result.specification, comparison=spec.question==='compare';
  const leftTitle=formatExperimentSide(spec.left), rightTitle=spec.right?formatExperimentSide(spec.right):'';
  const divergence=result.first_divergence;
  const statisticDivergence=result.first_statistic_divergence;
  const incomplete=result.evidence?.status==='incomplete';
  const badge=incomplete?'INCOMPLETE':comparison?(divergence?'DIVERGENCE':statisticDivergence?'DISTRIBUTION DIFFERS':'MATCH'):'FINITE COUNT';
  const badgeClass=incomplete?'incomplete':divergence||statisticDivergence?'counterexample':'verified';
  let table='';
  if (comparison) {
    table=`<div class="experiment-table-wrap"><table class="experiment-table"><thead><tr><th>n</th><th>${leftTitle}</th><th>${rightTitle}</th><th>Difference</th>${spec.statistic!=='none'?'<th>Distribution</th>':''}<th>Explore</th></tr></thead><tbody>${result.rows.map(row=>`<tr class="${!row.counts_match?'diverged-row':''}"><th scope="row">${row.n}</th><td>${formatCount(row.left_count)}</td><td>${formatCount(row.right_count)}</td><td class="difference ${row.difference===0?'zero':'nonzero'}">${row.difference>0?'+':''}${formatCount(row.difference)}</td>${spec.statistic!=='none'?`<td><span class="distribution-status ${row.distributions_match?'same':'different'}">${row.distributions_match?'Same':'Different'}</span></td>`:''}<td class="result-actions">${spec.statistic!=='none'?`<button class="text-button" data-show-distribution="${row.n}">Show buckets</button>`:''}<button class="text-button" data-object-side="left" data-object-n="${row.n}">Browse first</button><button class="text-button" data-object-side="right" data-object-n="${row.n}">Browse second</button></td></tr>`).join('')}</tbody></table></div>`;
  } else {
    table=`<div class="experiment-table-wrap"><table class="experiment-table"><thead><tr><th>n</th><th>${leftTitle}</th>${spec.statistic!=='none'?'<th>Statistic groups</th>':''}<th>Explore</th></tr></thead><tbody>${result.rows.map(row=>`<tr><th scope="row">${row.n}</th><td>${formatCount(row.left_count)}</td>${spec.statistic!=='none'?`<td>${row.left_distribution.length}</td>`:''}<td><button class="text-button" data-object-side="left" data-object-n="${row.n}">Browse members</button></td></tr>`).join('')}</tbody></table></div>`;
  }
  const takeaway=incomplete?`Cancelled during n=${result.evidence.cancelled_at_degree}. Rows shown are complete degrees only.`:divergence?`At n=${divergence.n}, the counts are ${formatCount(divergence.left_count)} and ${formatCount(divergence.right_count)}.`:comparison&&statisticDivergence?`The total counts match, but the ${escapeHtml(result.statistic_label.toLowerCase())} distributions first differ at n=${statisticDivergence.n}.`:result.notice;
  const relation=divergence?'≠':'=';
  const canFindWitnesses=divergence && spec.left.family===spec.right.family && divergence.left_degree===divergence.right_degree;
  const divergenceAction=canFindWitnesses?`<div class="discovery-actions"><button class="secondary" id="find-unmatched">Find exact unmatched words at n=${divergence.n}</button><span class="small muted">AC-Engine will search this finite degree and show class-membership witnesses.</span></div><div id="divergence-witnesses"></div>`:'';
  const refinementActions=comparison?`<div class="refinement-actions"><span class="small muted">Strengthen the comparison:</span>${[['ascents','ascents'],['ascent_runs','ascent runs'],['run_lengths','run-length profile'],['maximum','maximum'],['multiplicity_partition','multiplicity profile'],['first_occurrence_positions','first-occurrence positions'],['last_occurrence_positions','last-occurrence positions'],['run_start_positions','run-start positions']].map(([value,label])=>`<button class="text-button" data-refine-stat="${value}">By ${label}</button>`).join('')}</div>`:'';
  $('#experiment-result').innerHTML=`<section class="experiment-result card"><div class="experiment-result-top"><div><span class="result-kicker">BOUNDED RESULT</span><span class="status-chip ${badgeClass}">${badge}</span></div><h2>${escapeHtml(result.headline)}</h2><p class="result-equation">${leftTitle}${comparison?` <span aria-hidden="true">${relation}</span> ${rightTitle}`:''}</p><p class="result-takeaway">${escapeHtml(takeaway)}</p></div>${table}<div id="experiment-distribution"></div>${refinementActions}${divergenceAction}<div id="experiment-object-browser"></div><p class="finite-note">Finite evidence for this requested range; not a proof for all degrees.</p><details class="experiment-metadata"><summary>Reproducibility details</summary><div><span><b>Scanned objects</b>${formatCount(result.tested_objects)}</span><span><b>Runtime</b>${result.runtime_seconds}s</span><span><b>Refinement</b>${escapeHtml(result.statistic_label)}</span><span><b>Execution</b>${escapeHtml(result.evidence?.status||'finite')}</span></div><pre>${escapeHtml(JSON.stringify(spec,null,2))}</pre></details></section>`;
  $$('#experiment-result [data-object-side]').forEach(button=>button.addEventListener('click',()=>openObjectBrowser(button.dataset.objectSide,Number(button.dataset.objectN),0)));
  $$('#experiment-result [data-show-distribution]').forEach(button=>button.addEventListener('click',()=>showDistributionDetails(Number(button.dataset.showDistribution))));
  $$('#experiment-result [data-refine-stat]').forEach(button=>button.addEventListener('click',()=>refineExperiment(button.dataset.refineStat)));
  $('#find-unmatched')?.addEventListener('click',findUnmatched);
}

function showDistributionDetails(n) {
  const row=activeExperiment.rows.find(item=>item.n===n);
  if (!row) return;
  const root=$('#experiment-distribution');
  root.innerHTML=distributionDetails(row,activeExperiment.statistic_label);
  $('#close-distribution')?.addEventListener('click',()=>{root.innerHTML='';});
  root.scrollIntoView({behavior:'smooth',block:'nearest'});
}

async function refineExperiment(statistic) {
  const request={...activeExperiment.specification,statistic};
  $('#experiment-statistic').value=statistic;
  updateExperimentSentence();
  await runResearchJob('experiment',request,'#experiment-result','#experiment-run','#experiment-cancel',renderExperiment);
}

async function openObjectBrowser(side,n,offset=0,filters=null) {
  if (filters===null) {
    filters=objectBrowserState?.side===side && objectBrowserState?.n===n
      ? objectBrowserState.filters
      : {statistic:'',value:'',pattern_mode:'none',pattern:''};
  }
  objectBrowserState={side,n,offset,filters};
  const root=$('#experiment-object-browser');
  root.innerHTML='<div class="loading">Loading class members from AC-Engine…</div>';
  try {
    const page=await api('/api/experiment/objects',{specification:activeExperiment.specification,side,n,offset,limit:25,filters});
    const label=side==='left'?'First class':'Second class';
    const totalKey=side==='left'?'left_count':'right_count';
    const total=activeExperiment.rows.find(row=>row.n===n)?.[totalKey];
    const cards=page.objects.map(item=>`<article class="object-row"><div><span class="object-rank">#${formatCount(item.index)}</span><code>${escapeHtml(item.word.join(' '))}</code><span class="object-stats">ascents ${item.ascents} · runs ${escapeHtml(item.run_start_positions.join(', '))} · first ${escapeHtml(item.first_occurrence_positions.join(', '))} · last ${escapeHtml(item.last_occurrence_positions.join(', '))} · blocks ${escapeHtml(item.run_blocks.map(block=>`[${block.join(' ')}]`).join(' | '))} · max ${item.maximum} · multiplicities ${escapeHtml(item.multiplicity_partition.join(', '))}</span></div><button class="text-button" data-inspect-word="${escapeHtml(item.word.join(','))}">Inspect structure</button></article>`).join('');
    const rangeText=page.objects.length
      ? page.filters_active
        ? `filtered ranks ${formatCount(page.objects[0].index)}–${formatCount(page.objects[page.objects.length-1].index)}`
        : `${formatCount(page.objects[0].index)}–${formatCount(page.objects[page.objects.length-1].index)} of ${formatCount(total)} members`
      : 'no results';
    root.innerHTML=`<section class="object-browser card"><div class="browser-head"><div><span class="eyebrow">OBJECT BROWSER · ${escapeHtml(label)}</span><h3>Degree ${page.degree}</h3><p class="small muted">Members are generated by AC-Engine and filtered by this experiment. Add a statistic or pattern filter to narrow the list.</p></div><button class="icon-button" id="close-object-browser" aria-label="Close object browser">×</button></div><div class="browser-filter"><label>Statistic<select id="browser-stat"><option value="">Any</option><option value="ascents">Ascent count</option><option value="ascent_runs">Ascent runs</option><option value="run_lengths">Run-length profile</option><option value="maximum">Maximum</option><option value="distinct_values">Distinct values</option><option value="multiplicity_partition">Multiplicity profile</option><option value="first_occurrence_positions">First-occurrence positions</option><option value="last_occurrence_positions">Last-occurrence positions</option><option value="run_start_positions">Run-start positions</option></select></label><label>Equals<input id="browser-stat-value" value="${escapeHtml(filters.value||'')}" placeholder="e.g. 2 or 2,1,1" /></label><label>Pattern<select id="browser-pattern-mode"><option value="none">Any</option><option value="contain">Contains</option><option value="avoid">Avoids</option></select></label><label>Pattern word<input id="browser-pattern" value="${escapeHtml(filters.pattern||'')}" placeholder="e.g. 2122" /></label><button class="secondary" id="browser-apply">Apply filters</button></div>${cards||'<p class="muted">No members match these filters.</p>'}<div class="browser-controls"><span class="small muted">Showing ${rangeText} · scanned ${formatCount(page.scanned_objects)} generated words</span><div><button class="secondary" id="objects-prev" ${offset===0?'disabled':''}>Previous 25</button> <button class="secondary" id="objects-next" ${page.next_offset===null?'disabled':''}>Next 25</button></div></div></section>`;
    $('#browser-stat').value=filters.statistic||'';
    $('#browser-pattern-mode').value=filters.pattern_mode||'none';
    $('#browser-apply').addEventListener('click',()=>{
      const newFilters={statistic:$('#browser-stat').value,value:$('#browser-stat-value').value,pattern_mode:$('#browser-pattern-mode').value,pattern:$('#browser-pattern').value};
      openObjectBrowser(side,n,0,newFilters);
    });
    root.querySelectorAll('[data-inspect-word]').forEach(button=>button.addEventListener('click',()=>inspectExperimentWord(button.dataset.inspectWord)));
    $('#objects-prev')?.addEventListener('click',()=>openObjectBrowser(side,n,Math.max(0,offset-25),filters));
    $('#objects-next')?.addEventListener('click',()=>openObjectBrowser(side,n,page.next_offset,filters));
    $('#close-object-browser')?.addEventListener('click',()=>{root.innerHTML='';objectBrowserState=null;});
  } catch(e) { root.innerHTML=`<div class="error-box">${escapeHtml(e.message)}</div>`; }
}

async function findUnmatched() {
  const button=$('#find-unmatched');
  const result=activeExperiment.first_divergence;
  button.disabled=true; button.textContent='Searching for exact witnesses…';
  try {
    const data=await api('/api/experiment/unmatched',{specification:activeExperiment.specification,n:result.n});
    const renderWitness=(label,witness)=>witness?`<article class="witness-card"><span class="eyebrow">${escapeHtml(label)} ONLY</span><code>${escapeHtml(witness.word.join(' '))}</code><p>Ascents ${witness.ascents} · maximum ${witness.maximum} · multiplicities ${escapeHtml(witness.multiplicity_partition.join(', '))} · first occurrences at ${escapeHtml(witness.first_occurrence_positions.join(', '))} · blocks ${escapeHtml(witness.run_blocks.map(block=>`[${block.join(' ')}]`).join(' | '))}.</p><button class="text-button" data-inspect-word="${escapeHtml(witness.word.join(','))}">Inspect this witness</button></article>`:'';
    const root=$('#divergence-witnesses');
    const [leftInspection,rightInspection]=await Promise.all([
      data.left_only?api('/api/inspect',{word:data.left_only.word.join(',')}):Promise.resolve(null),
      data.right_only?api('/api/inspect',{word:data.right_only.word.join(',')}):Promise.resolve(null)
    ]);
    const structuralSide=(label,witness,inspection)=>{
      if (!witness||!inspection) return '';
      const positions=inspection.positions.map(p=>{
        const roles=[p.first&&'First',p.last&&'Last',p.asc_top&&'AscTop',p.asc_bottom&&'AscBottom',p.run_start&&'RunStart',p.run_end&&'RunEnd',p.defect_first_not_top&&'First≠Top',p.defect_top_not_first&&'Top≠First'].filter(Boolean);
        return `<span class="autopsy-position" title="${escapeHtml(p.reasons.join(' '))}"><b>${p.value}</b><small>${p.position}</small><i>${escapeHtml(roles.join(' · ')||'—')}</i></span>`;
      }).join('');
      const fibres=inspection.fibres.map(f=>`<tr><th>${f.value}</th><td>${escapeHtml(f.orientation)}</td><td>${escapeHtml(f.fibre.join(', '))}</td><td>${escapeHtml(f.gaps.filter(g=>g.lower_positions.length).map(g=>`${g.gap}: ${g.lower_positions.join(',')}`).join(' · ')||'none')}</td></tr>`).join('');
      const blocks=witness.run_blocks.map(block=>`<span class="block-chip">${escapeHtml(block.join(' '))}</span>`).join('<span class="block-separator">→</span>');
      return `<article class="autopsy-side"><span class="eyebrow">${escapeHtml(label)} ONLY</span><h4>${escapeHtml(inspection.word)}</h4><div class="autopsy-metrics"><span>height <b>${inspection.height}</b></span><span>ascents <b>${witness.ascents}</b></span><span>modified <b>${inspection.is_modified?'yes':'no'}</b></span><span>revised <b>${inspection.is_revised?'yes':'no'}</b></span><span>defects <b>${inspection.defect.size}</b></span></div><div class="autopsy-blocks"><span class="small muted">Engine-defined ascent runs</span><div>${blocks}</div></div><div class="autopsy-positions">${positions}</div><div class="experiment-table-wrap"><table><thead><tr><th>Value</th><th>Fibre orientation</th><th>Positions</th><th>Lower material in gaps</th></tr></thead><tbody>${fibres||'<tr><td colspan="4">No fibres</td></tr>'}</tbody></table></div><button class="text-button" data-inspect-word="${escapeHtml(witness.word.join(','))}">Open full sequence inspector</button></article>`;
    };
    root.innerHTML=`<section class="witness-panel card"><div><span class="eyebrow">FIRST COUNT DIVERGENCE · n=${data.n}</span><h3>Exact set-difference witnesses</h3><p class="small muted">Found by checking class membership on the same generated universe; scanned ${formatCount(data.tested_objects)} words. This is finite evidence.</p></div><div class="witness-grid">${renderWitness('First class',data.left_only)}${renderWitness('Second class',data.right_only)}</div><div class="autopsy-grid">${structuralSide('First class',data.left_only,leftInspection)}${structuralSide('Second class',data.right_only,rightInspection)}</div></section>`;
    root.querySelectorAll('[data-inspect-word]').forEach(el=>el.addEventListener('click',()=>inspectExperimentWord(el.dataset.inspectWord)));
  } catch(e) {
    $('#divergence-witnesses').innerHTML=`<div class="error-box">${escapeHtml(e.message)}</div>`;
  } finally { button.disabled=false; button.textContent=`Find exact unmatched words at n=${result.n}`; }
}

function inspectExperimentWord(word) {
  $('#inspect-word').value=word;
  setTab('inspector');
  runInspect();
}
$('#experiment-run').addEventListener('click',()=>runExperiment());

function txSide(which) {
  const mode=$(`#tx-${which}-mode`).value;
  const pattern=$(`#tx-${which}-pattern`).value.trim();
  return {family:$(`#tx-${which}-family`).value,rules:mode==='none'?[]:[{mode,pattern}]};
}
function transformFailure(row, inverse) {
  if (row.first_invalid) return ['Invalid output',row.first_invalid];
  if (row.first_target_failure) return ['Outside target class',row.first_target_failure];
  if (row.first_collision) return ['Collision',row.first_collision];
  if (row.first_missing_target) return ['Uncovered target',row.first_missing_target];
  if (inverse && row.first_inverse_failure) return ['Inverse failed',row.first_inverse_failure];
  if (row.first_statistic_failure) return ['Statistic changed',row.first_statistic_failure];
  return null;
}
function renderTransformExperiment(data) {
  const rows=data.rows;
  const incomplete=data.evidence?.status==='incomplete';
  const everyRowPasses=rows.every(row=>row.all_sources_land_in_target&&row.injective&&row.surjective&&(!data.inverse||row.inverse_successes===row.source_count)&&(!data.statistic||row.statistic_failures===0));
  const firstFailure=rows.find(row=>transformFailure(row,Boolean(data.inverse)));
  const headline=incomplete?`Cancelled during n=${data.evidence.cancelled_at_degree}`:everyRowPasses?`Finite checks pass through n=${rows[rows.length-1]?.n??'?'}`:`First failed check at n=${firstFailure?.n??rows[0]?.n??'?'}`;
  const rowHtml=rows.map(row=>{
    const match=row.all_sources_land_in_target&&row.injective&&row.surjective&&(!data.inverse||row.inverse_successes===row.source_count)&&(!data.statistic||row.statistic_failures===0);
    const inverseText=data.inverse?`${formatCount(row.inverse_successes)}/${formatCount(row.source_count)}`:'not defined';
    const statisticText=data.statistic?`${formatCount(row.statistic_preserved)} preserved · ${formatCount(row.statistic_failures)} changed`:'not selected';
    const degreeText=row.source_degree===row.target_degree?String(row.source_degree):`${row.source_degree} → ${row.target_degree}`;
    return `<tr class="${match?'':'diverged-row'}"><th>${degreeText}</th><td>${formatCount(row.source_count)}</td><td>${formatCount(row.cayley_outputs)}</td><td>${formatCount(row.target_hits)}</td><td>${formatCount(row.distinct_images)}</td><td>${formatCount(row.collisions)}</td><td>${formatCount(row.target_coverage)} / ${formatCount(row.target_count)}</td><td>${inverseText}</td><td>${escapeHtml(statisticText)}</td><td><button class="text-button" data-tx-detail="${row.n}">Why?</button></td></tr>`;
  }).join('');
  const parameterText=data.parameter===null||data.parameter===undefined?'':data.transformation==='insert_position'?` at cut ${data.parameter}`:` at position ${data.parameter}`;
  const transformLabel=`${data.transformation}${parameterText}`;
  const chipClass=incomplete?'incomplete':everyRowPasses?'verified':'counterexample';
  const chipText=incomplete?'INCOMPLETE':everyRowPasses?'CHECKS PASS':'CHECK FAILED';
  $('#tx-result').innerHTML=`<section class="transform-result card"><div class="experiment-result-top"><span class="result-kicker">FINITE TRANSFORMATION AUDIT</span><span class="status-chip ${chipClass}">${chipText}</span><h2>${escapeHtml(headline)}</h2><p class="result-equation">${escapeHtml(transformLabel)}${data.value===null||data.value===undefined?'':` · value ${data.value}`}${data.inverse?` · inverse candidate ${escapeHtml(data.inverse)}`:''}</p><p class="result-takeaway">${escapeHtml(data.notice)}</p></div><div class="experiment-table-wrap"><table class="experiment-table"><thead><tr><th>Source → target degree</th><th>Sources</th><th>Cayley outputs</th><th>In target</th><th>Distinct images</th><th>Collisions</th><th>Target coverage</th><th>Inverse recovery</th><th>Statistic</th><th>Trace</th></tr></thead><tbody>${rowHtml}</tbody></table></div><div id="tx-diagnostic"></div><details class="experiment-metadata"><summary>Exact specification and runtime</summary><div><span><b>Runtime</b>${data.runtime_seconds}s</span><span><b>Maximum source degree</b>10</span><span><b>Claim status</b>${escapeHtml(data.evidence?.status||'finite')}</span></div><pre>${escapeHtml(JSON.stringify(data.specification,null,2))}</pre></details><p class="finite-note">This is a bounded audit. It cannot establish an all-degree bijection theorem.</p></section>`;
  $$('#tx-result [data-tx-detail]').forEach(button=>button.addEventListener('click',()=>{
    const row=rows.find(item=>item.n===Number(button.dataset.txDetail));
    const failure=transformFailure(row,Boolean(data.inverse));
    const diag=$('#tx-diagnostic');
    if (!failure) { diag.innerHTML=`<div class="callout info">All reported checks pass at n=${row.n}; finite evidence only.</div>`; return; }
    const [title,witness]=failure;
    const source=Array.isArray(witness.source)?witness.source.join(' '):'';
    const output=Array.isArray(witness.output)?witness.output.join(' '):'';
    const details=Object.entries(witness).filter(([key])=>!['source','output'].includes(key)).map(([key,value])=>`<span><b>${escapeHtml(key.replaceAll('_',' '))}</b> ${escapeHtml(Array.isArray(value)?value.join(', '):String(value))}</span>`).join('');
    diag.innerHTML=`<section class="transform-diagnostic card"><span class="eyebrow">n=${row.n} · ${escapeHtml(title)}</span><h3>${source?`Source ${escapeHtml(source)}`:'Witness'}</h3>${output?`<p>Output <code>${escapeHtml(output)}</code></p>`:''}<div>${details}</div></section>`;
  }));
}
function updateTransformParameter() {
  const name=$('#tx-name').value;
  const parameterized=['prefix_lift','inverse_prefix_lift','insert_position','delete_position'].includes(name);
  const valued=['insert_position','delete_position'].includes(name);
  $('#tx-parameter-wrap').hidden=!parameterized;
  $('#tx-value-wrap').hidden=!valued;
  $('#tx-parameter-label').textContent=name==='insert_position'?'Insertion cut after 0-based position':name==='delete_position'?'Deleted position (1-based)':'Pivot position';
  $('#tx-parameter').min=name==='insert_position'?'0':'1';
  $('#tx-parameter-help').textContent=name==='insert_position'?'Cut 0 is before the first entry; cut 1 in 1,2,1 inserts between 1 and 2.':name==='delete_position'?'Positions start at 1; in 1,2,2,1, deleting position 3 removes the second 2.':'Positions start at 1; in 2,1,2, pivot 2 raises the earlier 2 to 3.';
  $('#tx-value-label').textContent=name==='delete_position'?'Expected value at deleted position':'Value level to insert';
  $('#tx-value-help').textContent=name==='delete_position'?'Choose the value at the removed position; position 3 in 1,2,2,1 has value 2.':'Choose an existing value; inserting value 2 into 1,2,1 after cut 1 gives 1,2,2,1.';
  $('#tx-description').textContent=OPTION_HELP['tx-name'][name];
  $('#tx-degree-effect').textContent=name==='insert_position'?'Target degree is n+1. Use start-stop, such as 1-6; target generation is checked too.':name==='delete_position'?'Target degree is n−1; start at n=2 or above. Use start-stop, such as 2-6.':'Use start-stop, such as 1-6. This transformation check is capped at 10.';
}
$('#tx-name').addEventListener('change',updateTransformParameter);
updateTransformParameter();
$('#tx-run').addEventListener('click',async()=>{
  const range=$('#tx-range').value.trim().match(/^(\d+)\s*[-–]\s*(\d+)$/);
  if (!range) { $('#tx-result').innerHTML='<div class="error-box">Enter a degree range such as 1-6.</div>'; return; }
  const transformation=$('#tx-name').value;
  const request={transformation,start:Number(range[1]),stop:Number(range[2]),statistic:$('#tx-statistic').value,source:txSide('source'),target:txSide('target')};
  if (['prefix_lift','inverse_prefix_lift','insert_position','delete_position'].includes(transformation)) request.parameter=Number($('#tx-parameter').value);
  if (['insert_position','delete_position'].includes(transformation)) request.value=Number($('#tx-value').value);
  await runResearchJob('transformation',request,'#tx-result','#tx-run','#tx-cancel',renderTransformExperiment);
});
restoreDraft();
renderPatternLane('left'); renderPatternLane('right');
validateExperimentSide('left'); validateExperimentSide('right'); updateExperimentValidity();

function renderStatus(data) {
  const overall=data.status.overall;
  $('#overall-status').className=`status-chip ${statusClass(overall.label)}`;
  $('#overall-status').textContent=statusText(overall);
  $('#overall-detail').textContent=overall.detail;
  const claims=[...data.status.claims].sort((a,b)=>(a.priority ?? 99)-(b.priority ?? 99));
  $('#claim-list').innerHTML=claims.map(c=>`<article class="claim claim-${statusClass(c.label)}"><span class="status-chip ${statusClass(c.label)}">${statusText(c)}</span><h3>${c.title}</h3><p>${c.detail}</p>${c.witness?`<p><code>${c.witness}</code></p>`:''}</article>`).join('');
  $('#contract-tasks').innerHTML=data.contract.tasks.map(x=>`<li>${x}</li>`).join('');
  $('#contract-rule').textContent=data.contract.rule;
}

async function boot() {
  try {
    const data=await api('/api/status'); renderStatus(data); $('#connection-state').textContent='Connected to AC-Engine';
    try { restoreResearchState(await api('/api/research-state')); }
    catch(_) { researchStateReady=true; updateExperimentValidity(); }
  } catch(e) {
    $('#connection-state').textContent='Engine unavailable';
    $('#overall-detail').textContent='Start the local Ascent Engine service to run experiments.';
    researchStateReady=true;
  }
}
boot();
