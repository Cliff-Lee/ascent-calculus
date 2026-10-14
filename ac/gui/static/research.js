// Local, bounded reference runs; all metadata is rendered as text, never HTML.
(() => {
  const element = id => document.getElementById(id);
  let job = null, timer = null, current = null, generation = 0;
  const notice = text => {element('research-notice').textContent = text;};
  async function request(action, body) {
    const response = await fetch('/api/research/' + action, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Research request failed');
    return result;
  }
  async function search(event) {
    if (event) event.preventDefault();
    try {
      const year = element('research-year').value;
      const result = await request('library', {query:element('research-query').value,author:element('research-author').value,
        year:year ? Number(year) : null,priority:element('research-priority').value || null});
      const select = element('research-work'); select.replaceChildren(new Option('Select a work',''));
      result.records.forEach(r => select.add(new Option(`${r.id} · ${r.title} · ${r.year} · ${r.priority}`,r.id)));
      notice(`${result.available_count} works · ${result.notice}`);
    } catch (error) {notice(error.message);}
  }
  element('research-search').addEventListener('submit',search);
  element('tab-research').addEventListener('click',() => {if (!current) search();});
  element('research-work').addEventListener('change',async event => {
    if (!event.target.value) return;
    try {
      generation++;if(timer)clearTimeout(timer);
      if(job && !element('research-cancel').disabled)await request('cancel',{id:job});
      element('research-run').disabled=false;element('research-cancel').disabled=true;
      current = await request('work',{id:event.target.value});
      element('research-detail').textContent = current.display_text;
      element('research-citations').replaceChildren();
      current.citations.forEach(c => {const link=document.createElement('a'); link.href=c.url; link.target='_blank'; link.rel='noopener noreferrer';
        link.textContent=`${c.citation_id} · ${c.location} · ${c.source_version}`; element('research-citations').append(link);});
      const methods=element('research-method');methods.replaceChildren();
      current.capabilities.forEach(c => methods.add(new Option(c.title,c.id)));
      element('research-result').textContent='Choose a mapped reference to inspect its exact finite evidence and remaining obligations.';
      element('research-objects').replaceChildren();
    } catch(error) {notice(error.message);}
  });
  async function poll(token) {
    try {
      const state=await request('job',{id:job});if(token!==generation)return;
      if (state.status==='running') {timer=setTimeout(() => poll(token),100);return;}
      element('research-run').disabled=false;element('research-cancel').disabled=true;
      notice(state.status);
      if (state.status==='completed') {
        element('research-result').textContent=state.display_text;
        element('research-objects').replaceChildren();
        state.result.inspectable_objects.forEach(item => {
          const button=document.createElement('button');button.type='button';button.textContent=`Inspect ${item.word.join(', ')} · ${item.label}`;
          button.addEventListener('click',async () => {
            try {const translated=await request('inspect',{word:item.word,value_base:item.value_base});
              element('research-inspector-context').textContent=`Research source ${translated.source_word} (base ${translated.source_value_base}) → positive engine ${translated.positive_engine_word}. ${item.label}`;
              element('inspect-word').value=translated.inspector_input; setTab('inspector'); await runInspect();
              notice(`Source base ${translated.source_value_base}: ${translated.source_word} → positive engine ${translated.positive_engine_word}`);
            } catch(error) {notice(error.message);}
          });element('research-objects').append(button);
        });
      } else if(state.result) element('research-result').textContent=state.result.detail;
    } catch(error) {notice(error.message);element('research-run').disabled=false;element('research-cancel').disabled=true;}
  }
  element('research-run').addEventListener('click',async () => {
    try {const result=await request('start',{method:element('research-method').value});job=result.id;
      element('research-run').disabled=true;element('research-cancel').disabled=false;
      element('research-result').textContent='Running isolated small reference…';element('research-objects').replaceChildren();
      notice('Finite independent check running; Cancel stops the worker.');generation++;poll(generation);
    } catch(error) {notice(error.message);}
  });
  element('research-cancel').addEventListener('click',async () => {
    generation++;if(timer) clearTimeout(timer);
    try {await request('cancel',{id:job});notice('Cancelled · no completed evidence recorded for this run.');
      element('research-run').disabled=false;element('research-cancel').disabled=true;
    } catch(error) {notice(error.message);}
  });
  element('research-pack').addEventListener('change',async event => {
    const file=event.target.files[0];if(!file)return;
    if(file.size>2000000) {notice('Research ZIP exceeds the 2 MB budget.');return;}
    try {const buffer=new Uint8Array(await file.arrayBuffer());let binary='';buffer.forEach(b => {binary+=String.fromCharCode(b);});
      await request('import',{archive_base64:btoa(binary)});await search();
    } catch(error) {notice('Import refused: '+error.message);}
  });
})();
