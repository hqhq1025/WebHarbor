let DATA, RUN_INDEX, state={selected:null,attempt:0,runId:null};
const $=id=>document.getElementById(id);
const cls=d=>`pill ${d||''}`;
const POINT_ACTIONS=new Set(['click','double_click','move']);
const VIEW_W=1280, VIEW_H=720;
function esc(s){return String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function pretty(obj){return JSON.stringify(obj??{},null,2)}
function decisionPill(d){return `<span class="${cls(d)}">${d||'unknown'}</span>`}
function hasLeakHint(text){return /candidate (title|product|course|to verify)|target answer|expected answer/i.test(text||'')}
function redactInstruction(text){return String(text||'').replace(/\s*Candidate (title|product|course) to verify after filtering:.*$/i,' [REDACTED candidate hint]').replace(/\s*Candidate .*$/i,' [REDACTED candidate hint]')}
function revealBlock(title, body, cls='sensitive'){return `<details class="${cls}"><summary>${esc(title)}</summary><pre>${esc(body||'')}</pre></details>`}
function resetSelect(id,label){const el=$(id); el.innerHTML=`<option value="">${label}</option>`; return el}
function initFilters(items){
  for(const [id,label,vals] of [['siteFilter','All sites',[...new Set(items.map(x=>x.site))]],['decisionFilter','All decisions',[...new Set(items.map(x=>x.decision))]],['policyFilter','All policies',[...new Set(items.map(x=>x.answer_policy))]],['tagFilter','All tags',[...new Set(items.flatMap(x=>[...(x.sft_tags||[]),...(x.judge_tags||[])])).values()]]]){
    const el=resetSelect(id,label); vals.filter(Boolean).sort().forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;el.appendChild(o)}); el.onchange=renderList;
  }
  $('search').oninput=renderList;
}
function initRunSelect(){const el=$('runSelect'); el.innerHTML=''; for(const r of RUN_INDEX.runs){const o=document.createElement('option');o.value=r.run_id;o.textContent=`${r.run_id} · train ${r.decision_counts?.train||0} / review ${r.decision_counts?.review||0} / reject ${r.decision_counts?.reject||0}`;el.appendChild(o)} el.value=state.runId||RUN_INDEX.default_run_id; el.onchange=()=>loadRun(el.value)}
function passFilters(x){const q=$('search').value.toLowerCase();if(q&&!JSON.stringify(x).toLowerCase().includes(q))return false;if($('siteFilter').value&&x.site!==$('siteFilter').value)return false;if($('decisionFilter').value&&x.decision!==$('decisionFilter').value)return false;if($('policyFilter').value&&x.answer_policy!==$('policyFilter').value)return false;const tag=$('tagFilter').value;if(tag&&![...(x.sft_tags||[]),...(x.judge_tags||[])].includes(tag))return false;return true}
function renderSummary(){const s=DATA.summary||{decision_counts:{}};$('summary').innerHTML=`<div class="metric"><strong>${s.decision_counts?.train||0}</strong><span>train</span></div><div class="metric"><strong>${s.decision_counts?.review||0}</strong><span>review</span></div><div class="metric"><strong>${s.decision_counts?.reject||0}</strong><span>reject</span></div>`;$('runSubtitle').textContent=`${DATA.run_id} · ${DATA.items.length} tasks · ${DATA.items.reduce((n,i)=>n+i.attempts.length,0)} attempts`}
function renderList(){const list=$('taskList');const items=DATA.items.filter(passFilters);const needsSelection=(!state.selected||!items.includes(state.selected))&&items[0];if(needsSelection){state.selected=items[0];state.attempt=Math.max(0,items[0].attempts.length-1)}list.innerHTML='';for(const x of items){const el=document.createElement('div');el.className='task-card'+(state.selected?.task_id===x.task_id?' active':'');el.innerHTML=`<div class="task-title">${esc(x.task_id)}</div><div class="task-meta">${decisionPill(x.decision)}<span class="pill">${esc(x.site)}</span><span class="pill">${esc(x.answer_policy)}</span><span class="pill">${x.attempts.length} attempts</span></div>`;el.onclick=()=>{state.selected=x;state.attempt=Math.max(0,x.attempts.length-1);renderAll()};list.appendChild(el)}if(needsSelection)renderAll(false)}
function renderHero(x){const leak=hasLeakHint(x.instruction);$('hero').innerHTML=`<div class="task-meta">${decisionPill(x.decision)}<span class="pill">${esc(x.site)}</span><span class="pill">${esc(x.family)}</span><span class="pill">${esc(x.answer_policy)}</span>${leak?'<span class="pill leak">prompt leak redacted</span>':''}</div><h2>${esc(x.task_id)}</h2><div class="instruction">${esc(redactInstruction(x.instruction||'(no trajectory attempt for this task)'))}</div>${leak?revealBlock('Reveal original instruction with candidate hint', x.instruction, 'sensitive leak-box'):''}${revealBlock('Show final answer', x.final_answer||'', 'sensitive final-answer-box')}`}
function renderPanels(x){$('qualityPanel').innerHTML=`<h3>Rule / SFT quality</h3><div class="kv compact"><div>Rule OK</div><div>${esc(x.rule_ok)}</div><div>SFT score</div><div>${esc(x.sft_quality_score)}</div><div>Recommendation</div><div>${esc(x.sft_recommendation)}</div><div>Reasons</div><div>${esc((x.reasons||[]).join(', ')||'none')}</div></div><div class="tags">${(x.sft_tags||[]).map(t=>`<span class="pill">${esc(t)}</span>`).join('')}</div><details><summary>Final check / metrics (may contain answer tokens)</summary><pre>${esc(pretty({final_answer_check:x.final_answer_check,state_diff_check:x.state_diff_check,metrics:x.sft_metrics}))}</pre></details>`;$('judgePanel').innerHTML=`<h3>54mini judge</h3><div class="kv compact"><div>Verdict</div><div>${esc(x.judge_verdict)}</div><div>Success</div><div>${esc(x.judge_success_score)}</div><div>SFT quality</div><div>${esc(x.judge_sft_quality_score)}</div></div><div class="tags">${(x.judge_tags||[]).map(t=>`<span class="pill">${esc(t)}</span>`).join('')}</div><details class="sensitive"><summary>Reveal judge rationale (may reveal answer)</summary><pre>${esc(x.judge_rationale||'')}</pre></details><details><summary>Failure modes</summary><pre>${esc(pretty(x.judge_failure_modes||[]))}</pre></details>`}
function renderAttempts(x){const tabs=$('attemptTabs');tabs.innerHTML='';x.attempts.forEach((a,i)=>{const b=document.createElement('button');b.className='attempt-tab'+(i===state.attempt?' active':'');b.textContent=`${a.attempt_id} · ${a.status} · ${a.steps.length} steps`;b.onclick=()=>{state.attempt=i;renderAll(false)};tabs.appendChild(b)})}
function actionLabel(a,idx){const t=a.type||a.action;if(t==='click'||t==='double_click')return `${idx+1}. ${t} (${a.x}, ${a.y})`;if(t==='type')return `${idx+1}. type “${String(a.text||'').slice(0,80)}”`;if(t==='keypress')return `${idx+1}. key ${Array.isArray(a.keys)?a.keys.join('+'):a.key}`;if(t==='scroll')return `${idx+1}. scroll ${a.scroll_x||a.dx||0}, ${a.scroll_y||a.dy||0}`;if(t==='wait')return `${idx+1}. wait`;if(t==='screenshot')return `${idx+1}. screenshot`;return `${idx+1}. ${t}`}
function actionClass(a){const t=a.type||a.action;if(['click','double_click'].includes(t))return'click';if(t==='type')return'type';if(t==='keypress')return'key';if(t==='scroll')return'scroll';return'other'}
function actionRaw(a){return Object.entries(a).filter(([k])=>k!=='action').map(([k,v])=>`${k}: ${typeof v==='object'?JSON.stringify(v):v}`).join('\n')}
function markerPos(a){
  const x=Number.isFinite(+a.x)?+a.x:VIEW_W-48;
  const y=Number.isFinite(+a.y)?+a.y:VIEW_H/2;
  return {left:(x/VIEW_W*100).toFixed(3), top:(y/VIEW_H*100).toFixed(3)};
}
function clamp(n,min,max){return Math.max(min,Math.min(max,n))}
function scrollArrow(a){
  const dy=+(a.scroll_y??a.dy??0), dx=+(a.scroll_x??a.dx??0);
  if(Math.abs(dx)>Math.abs(dy)) return dx>0?'→':'←';
  return dy>=0?'↓':'↑';
}
function scrollMagnitude(a){
  const dy=Math.abs(+(a.scroll_y??a.dy??0)), dx=Math.abs(+(a.scroll_x??a.dx??0));
  const mag=Math.max(dx,dy);
  if(!Number.isFinite(mag) || mag===0) return '0';
  if(mag<400) return 'small';
  if(mag<900) return 'medium';
  return 'large';
}
function scrollDirection(a){
  const dy=+(a.scroll_y??a.dy??0), dx=+(a.scroll_x??a.dx??0);
  if(Math.abs(dx)>Math.abs(dy)) return dx>0?'right':'left';
  return dy>=0?'down':'up';
}
function scrollAnchor(a,dir){
  let left=Number.isFinite(+a.x)?+a.x/VIEW_W*100:92;
  let top=Number.isFinite(+a.y)?+a.y/VIEW_H*100:50;
  left=clamp(left,8,92); top=clamp(top,8,92);
  if(dir==='down') top=clamp(top,8,80);
  if(dir==='up') top=clamp(top,20,92);
  if(dir==='right') left=clamp(left,8,82);
  if(dir==='left') left=clamp(left,18,92);
  return {left:left.toFixed(3),top:top.toFixed(3)};
}
function scrollVector(a,i){
  const dir=scrollDirection(a), size=scrollMagnitude(a);
  const dy=Math.abs(+(a.scroll_y??a.dy??0)), dx=Math.abs(+(a.scroll_x??a.dx??0));
  const len=clamp(Math.round(Math.max(dx,dy)/8),48,104);
  const box=(len+32)*2, c=box/2, r=15, gap=8;
  let x1=c,y1=c,x2=c,y2=c,head='';
  if(dir==='down'){y1=c+r+gap;y2=y1+len;head=`${c},${y2} ${c-10},${y2-14} ${c+10},${y2-14}`;y2-=8}
  if(dir==='up'){y1=c-r-gap;y2=y1-len;head=`${c},${y2} ${c-10},${y2+14} ${c+10},${y2+14}`;y2+=8}
  if(dir==='right'){x1=c+r+gap;x2=x1+len;head=`${x2},${c} ${x2-14},${c-10} ${x2-14},${c+10}`;x2-=8}
  if(dir==='left'){x1=c-r-gap;x2=x1-len;head=`${x2},${c} ${x2+14},${c-10} ${x2+14},${c+10}`;x2+=8}
  const p=scrollAnchor(a,dir), label=scrollArrow(a), title=esc(actionLabel(a,i));
  return `<svg class="scroll-vector ${dir} ${size}" style="left:${p.left}%;top:${p.top}%;width:${box}px;height:${box}px" viewBox="0 0 ${box} ${box}" title="${title}" aria-label="${title}"><line class="scroll-vector-line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"></line><polygon class="scroll-vector-head" points="${head}"></polygon><circle class="scroll-vector-badge" cx="${c}" cy="${c}" r="${r}"></circle><text class="scroll-vector-index" x="${c}" y="${c+4}">${i+1}</text><text class="scroll-vector-dir" x="${c}" y="${c-r-7}">${label}</text></svg>`;
}
function markers(actions){return actions.map((a,i)=>{const t=a.type||a.action;if(POINT_ACTIONS.has(t)&&Number.isFinite(+a.x)&&Number.isFinite(+a.y)){const p=markerPos(a);return `<div class="marker ${t}" style="left:${p.left}%;top:${p.top}%" title="${esc(actionLabel(a,i))}">${i+1}</div>`}if(t==='scroll')return scrollVector(a,i); if(t==='drag'){const s=a.start||{x:a.x,y:a.y};const e=a.end||{x:a.to_x,y:a.to_y};return[s,e].map((p,j)=>Number.isFinite(+p.x)&&Number.isFinite(+p.y)?`<div class="marker drag" style="left:${(+p.x/VIEW_W*100).toFixed(3)}%;top:${(+p.y/VIEW_H*100).toFixed(3)}%" title="drag ${j?'end':'start'}">${i+1}${j?'b':'a'}</div>`:'').join('')}return''}).join('')}
function renderTimeline(x){const a=x.attempts[state.attempt];const root=$('timeline');if(!a){root.innerHTML='<div class="empty">No attempt for this task. Check manifest/judge API failure.</div>';return}root.innerHTML=a.steps.map((s,i)=>{const before=s.screenshot_before_url||s.screenshot_url;const after=s.screenshot_after_url||s.screenshot_url;return `<article class="step"><div class="shot-wrap">${before?`<div class="shot-caption">before action</div><img class="shot" src="${esc(before)}" data-full="${esc(before)}" loading="lazy"/>${markers(s.actions||[])}${after&&after!==before?`<a class="after-link" href="${esc(after)}" target="_blank" rel="noreferrer">after screenshot</a>`:''}`:'<div class="empty">No screenshot</div>'}</div><div><div class="step-head"><h3>Step ${s.step}</h3><span class="pill">${(s.actions||[]).length} actions</span></div><div class="url">${esc(s.url_before||'')} → ${esc(s.url_after||'')}</div><div class="action-list">${(s.actions||[]).map((action,idx)=>`<div class="action-card ${actionClass(action)}"><div class="action-label">${esc(actionLabel(action,idx))}</div><details><summary>raw</summary><pre>${esc(actionRaw(action))}</pre></details></div>`).join('')}</div>${(a.responses||[])[i]?`<details class="response"><summary>response summary</summary><pre>${esc(pretty((a.responses||[])[i]))}</pre></details>`:''}</div></article>`}).join('');root.querySelectorAll('.shot').forEach(img=>img.onclick=()=>{$('dialogImage').src=img.dataset.full;$('imageDialog').showModal()})}
function renderAll(updateList=true){const x=state.selected;if(!x)return;renderHero(x);renderPanels(x);renderAttempts(x);renderTimeline(x);if(updateList)renderList()}
async function loadRun(runId){state.runId=runId;const meta=RUN_INDEX.runs.find(r=>r.run_id===runId);DATA=await fetch(meta.data_url + '?v=' + Date.now()).then(r=>r.json());state.selected=null;state.attempt=0;renderSummary();initFilters(DATA.items);renderList()}
$('closeDialog').onclick=()=>$('imageDialog').close();
fetch('runs_index.json?v=' + Date.now()).then(r=>r.json()).then(async idx=>{RUN_INDEX=idx;state.runId=idx.default_run_id;initRunSelect();await loadRun(state.runId)});
