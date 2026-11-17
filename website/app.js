/* The interface reads reviewed aggregate results. Filters never recompute official ranks. */
(() => {
  'use strict';
  const DATA = JSON.parse(document.getElementById('study-data').textContent);
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = (value, digits=1) => Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-US', {minimumFractionDigits:digits,maximumFractionDigits:digits}) : '—';
  const signed = (value,digits=1) => `${Number(value)>=0?'+':''}${fmt(value,digits)}`;
  const initials = (name) => name.split(/\s+/).map(x=>x[0]).filter(Boolean).slice(0,2).join('');
  const lookup = (role,id) => DATA.players[role].find(p=>p.player_id===Number(id));
  const selected = (role) => DATA.players[role].filter(p=>p.rank<=10).sort((a,b)=>a.rank-b.rank);
  const state={role:'batters',pool:'selected',search:'',group:'all',coverage:'all',sort:'score',view:'table',compare:new Set(),profile:null};
  let toastTimer;

  function toast(message) {
    $('toast').textContent=message;$('toast').classList.add('show');
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('show'),4000);
  }
  async function copy(text,message) {
    try {
      if(navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
      else {
        const t=document.createElement('textarea');t.value=text;t.style.position='fixed';t.style.opacity='0';document.body.append(t);t.select();
        const ok=document.execCommand('copy');t.remove();if(!ok) throw new Error('Copy unavailable');
      }
      toast(message);
    } catch {toast('Clipboard unavailable. You can select and copy the player names directly.');}
  }
  function filteredPlayers() {
    let list=DATA.players[state.role].filter(p=>state.pool==='all'||p.rank<=10);
    if(state.search.trim())list=list.filter(p=>p.name.toLowerCase().includes(state.search.trim().toLowerCase()));
    if(state.group!=='all')list=list.filter(p=>p.role.group===state.group);
    if(state.coverage==='ipl')list=list.filter(p=>p.ipl_p_balls>0);
    if(state.coverage==='t20i')list=list.filter(p=>p.ipl_p_balls===0);
    return list.sort((a,b)=>state.sort==='sample'?b.p_balls-a.p_balls||a.rank-b.rank:state.sort==='uplift'?b.uplift-a.uplift||a.rank-b.rank:state.sort==='name'?a.name.localeCompare(b.name):a.rank-b.rank);
  }
  function roleOptions() {
    const groups=state.role==='batters'?['Opening','Middle order','Late order']:['Powerplay','Middle','Death'];
    $('role-filter').innerHTML='<option value="all">All roles</option>'+groups.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
  }
  function setRole(role) {
    state.role=role;state.group='all';state.compare.clear();roleOptions();renderTray();
    document.querySelectorAll('[data-role]').forEach(b=>{const active=b.dataset.role===role;b.classList.toggle('active',active);b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;});
    $('performance-header').textContent=role==='batters'?'Pressure SR':'Pressure economy';
    renderPlayers();
  }
  function renderPlayers() {
    const list=filteredPlayers();const total=state.pool==='selected'?10:DATA.players[state.role].length;
    $('results-count').textContent=`${list.length} of ${total} ${state.pool==='selected'?'final selections':'eligible entries'} · ${state.role==='batters'?'Batting':'Bowling'}`;
    $('player-search').placeholder=state.pool==='selected'?'Search the selections':`Search all ${total} eligible entries`;
    $('empty-state').hidden=list.length>0;
    $('table-view').hidden=state.view!=='table'||!list.length;
    $('chart-view').hidden=state.view!=='chart'||!list.length;
    $('view-table').classList.toggle('active',state.view==='table');$('view-chart').classList.toggle('active',state.view==='chart');
    $('view-table').setAttribute('aria-pressed',String(state.view==='table'));$('view-chart').setAttribute('aria-pressed',String(state.view==='chart'));
    const max=Math.max(...DATA.players[state.role].map(p=>p.score),1);
    $('player-rows').innerHTML=list.map(p=>`<tr data-player="${p.player_id}"><td><span class="rank-number ${p.rank<=10?'is-top':''}">${String(p.rank).padStart(2,'0')}</span></td><td><div class="player-cell"><span class="player-avatar" aria-hidden="true">${esc(initials(p.name))}</span><div><button class="player-name" data-profile="${p.player_id}">${esc(p.name)}</button>${p.rank<=10?'<span class="selected-label">TOP 10</span>':''}<div class="player-sub">${esc(p.role.label)}<span class="mobile-sample"> · ${fmt(p.p_balls,0)} ${state.role==='batters'?'balls':'opps'} / ${p.p_matches} matches</span></div></div></div></td><td><span class="sample-main">${fmt(p.p_balls,0)} ${state.role==='batters'?'balls':'opps'}</span><span class="sample-sub">${p.p_matches} pressure matches</span></td><td><span class="performance-value">${fmt(state.role==='batters'?p.pressure_strike_rate:p.pressure_economy,state.role==='batters'?1:2)}</span><span class="sample-sub">${state.role==='batters'?`${p.outs} personal dismissals`:`${p.wickets} credited wickets`}</span></td><td><span class="uplift ${p.uplift>=0?'positive':'negative'}">${signed(p.uplift)}</span></td><td><span class="selection-score">${fmt(p.score,2)}</span><span class="score-meter"><span style="--score-width:${Math.max(0,p.score)/max*100}%"></span></span></td><td><div class="row-actions"><label class="compare-check"><input type="checkbox" data-compare="${p.player_id}" aria-label="Compare ${esc(p.name)}" ${state.compare.has(p.player_id)?'checked':''}></label><button class="details-button" data-profile="${p.player_id}" aria-label="Open ${esc(p.name)} profile">↗</button></div></td></tr>`).join('');
    if(state.view==='chart'&&list.length)renderUncertainty(list);
  }
  function renderUncertainty(list) {
    const shown=list.slice(0,25),left=175,right=45,width=960,row=34,top=30,bottom=42,height=top+shown.length*row+bottom;
    let lo=Math.min(0,...shown.map(p=>p.ci_low)),hi=Math.max(1,...shown.map(p=>p.ci_high));const pad=(hi-lo)*.08;lo-=pad;hi+=pad;
    const x=v=>left+(v-lo)/(hi-lo)*(width-left-right);
    let svg=`<svg class="uncertainty-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Robust rating estimates, conservative scores and ninety percent match-resample bands">`;
    for(let i=0;i<=5;i++){const v=lo+(hi-lo)*i/5,xx=x(v);svg+=`<line x1="${xx}" y1="12" x2="${xx}" y2="${height-bottom+5}" stroke="#e9ecf0"/><text x="${xx}" y="${height-12}" fill="#68717d" font-size="10" text-anchor="middle">${fmt(v,0)}</text>`;}
    svg+=`<line x1="${x(0)}" y1="12" x2="${x(0)}" y2="${height-bottom+5}" stroke="#bec6d2"/>`;
    shown.forEach((p,i)=>{const y=top+i*row;svg+=`<g class="chart-player" role="button" tabindex="0" data-profile="${p.player_id}" aria-label="View ${esc(p.name)}, selection score ${fmt(p.score,2)}"><title>${esc(p.name)}: score ${fmt(p.score,2)}, estimate ${fmt(p.rating,2)}, 90% band ${fmt(p.ci_low,2)} to ${fmt(p.ci_high,2)}</title><text x="0" y="${y+4}" fill="#152b4c" font-size="11">${String(p.rank).padStart(2,'0')}  ${esc(p.name)}</text><line x1="${x(p.ci_low)}" y1="${y}" x2="${x(p.ci_high)}" y2="${y}" stroke="#b3c1d2" stroke-width="3"/><circle cx="${x(p.rating)}" cy="${y}" r="4" fill="#152b4c"/><rect x="${x(p.score)-3}" y="${y-3}" width="6" height="6" fill="#cb0c72" transform="rotate(45 ${x(p.score)} ${y})"/><text x="${width-2}" y="${y+4}" fill="#152b4c" font-size="11" text-anchor="end">${fmt(p.score,2)}</text></g>`;});
    svg+='</svg>';
    $('chart-view').innerHTML=svg+`<div class="plot-legend"><span><i class="legend-line"></i>90% match-resample band</span><span><i class="legend-dot"></i>Robust estimate</span><span><i class="legend-dot legend-score"></i>Conservative selection score</span></div>${list.length>25?`<p class="fine-print">The plot shows the first 25 of ${list.length} matching entries in the current sort order. Filter by player name for a specific comparison.</p>`:''}`;
  }
  function toggleCompare(role,id) {
    id=Number(id);if(role!==state.role)setRole(role);
    if(state.compare.has(id))state.compare.delete(id);
    else if(state.compare.size<2)state.compare.add(id);
    else toast('Compare two players at a time. Clear one selection to add another.');
    renderPlayers();renderTray();
  }
  function renderTray() {
    const ids=[...state.compare],players=ids.map(id=>lookup(state.role,id));$('compare-tray').hidden=!ids.length;
    $('compare-tray-label').innerHTML=`<strong>${players.map(p=>esc(p.name)).join(' + ')}</strong><span>${ids.length===1?'Choose one more player':'Two players ready to compare'}</span>`;
    $('compare-tray-open').disabled=ids.length!==2;
  }
  function advantageChart(p,domain) {
    const w=420,left=65,right=36,lo=Math.min(0,domain[0]),hi=Math.max(1,domain[1]);const span=hi-lo||1;const x=v=>left+(v-lo)/span*(w-left-right);const zero=x(0);
    return `<div class="advantage-chart"><p>Adjusted advantage vs context · per 100</p><svg viewBox="0 0 ${w} 76" role="img" aria-label="Pressure advantage ${fmt(p.pressure_advantage,1)}, usual advantage ${fmt(p.usual_advantage,1)}"><line x1="${zero}" y1="1" x2="${zero}" y2="59" stroke="#c3cbd7" stroke-dasharray="3 3"/>${[['Pressure',p.pressure_advantage,'#cb0c72'],['Usual',p.usual_advantage,'#687c98']].map(([label,value,color],i)=>`<text x="0" y="${18+i*29}" fill="#68717d" font-size="10">${label}</text><rect x="${Math.min(zero,x(value))}" y="${7+i*29}" width="${Math.max(1,Math.abs(x(value)-zero))}" height="15" rx="2" fill="${color}"/><text x="${x(value)+(value>=0?6:-6)}" y="${18+i*29}" text-anchor="${value>=0?'start':'end'}" fill="#152b4c" font-size="10">${signed(value)}</text>`).join('')}<text x="${zero}" y="73" fill="#8b95a3" font-size="8" text-anchor="middle">0</text></svg></div>`;
  }
  function compareCard(p,role,domain) {
    const bat=role==='batters';
    return `<article class="compare-card"><div class="compare-card-heading"><div><p class="compare-rank">${p.rank<=10?'FINAL SELECTION':'ELIGIBLE ENTRY'} #${p.rank}</p><h3>${esc(p.name)}</h3><p class="profile-role">${esc(p.role.label)}</p></div><div class="compare-card-score">${fmt(p.score,2)}<small>Selection score</small></div></div>${advantageChart(p,domain)}<div class="compare-card-stats"><div><strong>${fmt(p.p_balls,0)}</strong><span>Pressure ${bat?'balls':'opportunities'}<br>across ${p.p_matches} matches</span></div><div><strong>${fmt(bat?p.pressure_strike_rate:p.pressure_economy,bat?1:2)}</strong><span>Pressure ${bat?'strike rate':'economy'}<br>usual: ${fmt(bat?p.normal_strike_rate:p.normal_economy,bat?1:2)}</span></div><div><strong>${signed(p.uplift)}</strong><span>Adjusted uplift / 100<br>vs usual level</span></div></div><div class="comparison-band"><span>90% rating band: <strong>${fmt(p.ci_low)} to ${fmt(p.ci_high)}</strong></span><span>Positive matches: <strong>${fmt(p.positive_pressure_match_pct)}%</strong></span></div><button class="text-link profile-compare-link" data-profile="${p.player_id}" data-profile-role="${role}" style="border:0;background:transparent;margin-top:14px;padding-left:0">Full player evidence ↗</button></article>`;
  }
  function setupComparison(role,ids=[]) {
    $('compare-role').value=role;
    const options=DATA.players[role].map(p=>`<option value="${p.player_id}">#${p.rank} · ${esc(p.name)}</option>`).join('');
    $('compare-a').innerHTML=options;$('compare-b').innerHTML=options;
    $('compare-a').value=ids[0]||DATA.players[role][0].player_id;$('compare-b').value=ids[1]||DATA.players[role][1].player_id;renderComparison();
  }
  function renderComparison() {
    const role=$('compare-role').value,a=lookup(role,$('compare-a').value),b=lookup(role,$('compare-b').value);
    const values=[a.pressure_advantage,a.usual_advantage,b.pressure_advantage,b.usual_advantage];
    const domain=[Math.min(...values)*1.3,Math.max(...values)*1.3];
    $('comparison-content').innerHTML=`<div class="compare-grid">${compareCard(a,role,domain)}${compareCard(b,role,domain)}</div>`;
  }
  function profileLine(label,value) {return `<div class="stat-line"><span>${label}</span><strong>${value}</strong></div>`;}
  function openProfile(role,id,updateUrl=true) {
    const p=lookup(role,id);if(!p)return;state.profile={role,id:p.player_id};const bat=role==='batters';
    const phaseEntries=['Powerplay','Middle','Death'].map(phase=>profileLine(phase,`${fmt(p.role.phases[phase]||0,0)} ${bat?'balls':'opps'}`)).join('');
    $('player-profile').innerHTML=`<div class="profile-header"><p class="profile-overline">${bat?'BATTER':'BOWLER'} · ${p.rank<=10?'FINAL TOP 10':'ELIGIBLE POOL'} · RANK #${p.rank}</p><h2 id="player-title">${esc(p.name)}</h2><p class="profile-role">${esc(p.role.label)}${bat?` · Modal batting position ${p.role.position}`:` · ${esc(p.role.bowling_type)}`}</p></div><div class="profile-body"><div class="profile-score-row"><div><div class="profile-score-value">${fmt(p.score,2)}</div><div class="profile-score-label">Conservative selection score / 100 opportunities</div></div><button class="button button-outline button-small" id="profile-add-compare">Add to comparison <span aria-hidden="true">+</span></button></div><div class="profile-stats"><div><strong>${fmt(p.p_balls,0)}</strong><span>Pressure ${bat?'balls':'opportunities'}</span></div><div><strong>${p.p_matches}</strong><span>Pressure matches</span></div><div><strong>${signed(p.uplift)}</strong><span>Adjusted uplift / 100</span></div></div><div class="profile-evidence"><div><h3>Pressure vs ordinary</h3>${profileLine(bat?'Pressure strike rate':'Pressure economy',fmt(bat?p.pressure_strike_rate:p.pressure_economy,bat?1:2))}${profileLine(bat?'Ordinary strike rate':'Ordinary economy',fmt(bat?p.normal_strike_rate:p.normal_economy,bat?1:2))}${profileLine(bat?'Pressure runs / dismissals':'Pressure wickets / runs',bat?`${p.runs} / ${p.outs}`:`${p.wickets} / ${p.conceded}`)}${profileLine('Positive pressure matches',`${fmt(p.positive_pressure_match_pct)}% (${p.positive_pressure_matches}/${p.p_matches})`)}${profileLine('Resampled top-10 frequency',`${fmt(p.top10_bootstrap_pct)}%`)}</div><div><h3>Where the evidence comes from</h3>${phaseEntries}${profileLine('IPL pressure exposure',`${fmt(p.ipl_p_balls,0)} ${bat?'balls':'opps'}`)}${profileLine('T20I pressure exposure',`${fmt(p.p_balls-p.ipl_p_balls,0)} ${bat?'balls':'opps'}`)}</div></div><div class="profile-band"><strong>Robust estimate ${fmt(p.rating,2)}</strong> · 90% match-resample band: <strong>${fmt(p.ci_low,2)} to ${fmt(p.ci_high,2)}</strong>.<br>These bands condition on fitted models and eligibility. Resampled top-10 frequency is a stability diagnostic, not a probability that a player is truly top 10.</div><div class="profile-actions"><button class="button button-primary button-small" id="profile-copy-name">Copy player name ⧉</button><button class="button button-outline button-small" id="profile-copy-link">Copy profile link ↗</button><span class="fine-print" style="margin:0;align-self:center">Source player ID: ${p.player_id}</span></div></div>`;
    $('profile-add-compare').addEventListener('click',()=>{toggleCompare(role,p.player_id);$('player-dialog').close();});
    $('profile-copy-name').addEventListener('click',()=>copy(p.name,`${p.name} copied`));
    $('profile-copy-link').addEventListener('click',()=>{const u=new URL(location.href);u.search='';u.searchParams.set('role',role);u.searchParams.set('player',p.player_id);copy(u.toString(),'Player profile link copied');});
    if(!$('player-dialog').open)$('player-dialog').showModal();
    if(updateUrl)try{const u=new URL(location.href);u.searchParams.set('role',role);u.searchParams.set('player',p.player_id);history.replaceState(null,'',u);}catch{}
  }
  function closeProfile() {
    state.profile=null;
    try{const u=new URL(location.href);u.searchParams.delete('player');history.replaceState(null,'',u);}catch{}
  }
  function renderHero() {
    $('hero-leaders').innerHTML=['batters','bowlers'].map(role=>{const p=selected(role)[0];return `<div class="leader-row"><div><span class="leader-role">#1 ${role==='batters'?'BATTER':'BOWLER'}</span><strong>${esc(p.name)}</strong></div><div class="leader-track" aria-hidden="true"><span style="width:${p.score/30*100}%"></span></div><span class="leader-score">${fmt(p.score,2)}</span></div>`;}).join('');
  }
  function renderCoverage() {
    $('role-coverage').innerHTML=['batters','bowlers'].map(role=>{
      const picks=selected(role),groups=role==='batters'?['Opening','Middle order','Late order']:['Powerplay','Middle','Death'];
      const rows=groups.map(g=>{const n=picks.filter(p=>p.role.group===g).length;return `<div class="coverage-row"><span>${g==='Middle'?'Middle overs':g==='Death'?'Death overs':g}</span><span class="coverage-track"><span style="width:${n/10*100}%"></span></span><strong>${n}</strong></div>`;}).join('');
      return `<article><div class="coverage-heading"><h3>${role==='batters'?'Batting positions':'Bowling phases'}</h3><span class="data-label">FINAL 10</span></div>${rows}<p class="coverage-names">${role==='batters'?'Positions are classified by the modal batting order in the reference pressure sample.':'Phases are classified by the largest number of reference pressure opportunities, across both innings.'}</p></article>`;
    }).join('');
  }
  function renderValidation() {
    const v=DATA.validation;
    $('validation-metrics').innerHTML=[[(100*v.accuracy).toFixed(2)+'%','Pre-ball win accuracy',`95% match-bootstrap interval: ${fmt(v.accuracy_interval_95[0]*100,2)}–${fmt(v.accuracy_interval_95[1]*100,2)}%`],[fmt(v.brier,4),'Brier score',`Neutral 50% baseline: ${fmt(v.neutral_brier,4)} · lower is better`],[fmt(v.auc,4),'ROC AUC','306 held-out matches · 72,484 delivery states']].map(([value,label,note])=>`<div class="validation-metric"><strong>${value}</strong><span>${label}</span><p>${note}</p></div>`).join('');
    $('persistence-values').innerHTML=['batters','bowlers'].map(role=>{const d=v[role+'_temporal'];return `<div class="persistence-row"><div>${role==='batters'?'Batters':'Bowlers'}<small>${d.common_eligible} eligible in both periods · top-10 overlap ${d.early_top10_late_top10}/10</small></div><strong>${fmt(d.early_late_spearman,3)}</strong></div>`;}).join('');
    const w=520,h=280,left=42,right=16,top=17,bottom=42,x=v=>left+v*(w-left-right),y=v=>h-bottom-v*(h-top-bottom);
    let svg=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Chronological model calibration: predicted win probability compared with observed win rate">`;
    for(let i=0;i<=5;i++){const v=i/5;svg+=`<line x1="${left}" x2="${w-right}" y1="${y(v)}" y2="${y(v)}" stroke="#e4e7ec"/><text x="${left-9}" y="${y(v)+3}" text-anchor="end" font-size="9" fill="#68717d">${v.toFixed(1)}</text><text x="${x(v)}" y="${h-bottom+18}" text-anchor="middle" font-size="9" fill="#68717d">${v.toFixed(1)}</text>`;}
    svg+=`<line x1="${x(0)}" y1="${y(0)}" x2="${x(1)}" y2="${y(1)}" stroke="#a5b3c7" stroke-width="1.5" stroke-dasharray="5 4"/><polyline points="${DATA.calibration.map(p=>`${x(p.predicted)},${y(p.actual)}`).join(' ')}" fill="none" stroke="#cb0c72" stroke-width="2"/>`;
    DATA.calibration.forEach(p=>svg+=`<circle cx="${x(p.predicted)}" cy="${y(p.actual)}" r="4" fill="#cb0c72"><title>Predicted ${fmt(p.predicted*100)}%, observed ${fmt(p.actual*100)}%; ${fmt(p.deliveries,0)} delivery states</title></circle>`);
    svg+=`<text x="${(left+w-right)/2}" y="${h-2}" text-anchor="middle" font-size="10" fill="#68717d">Predicted win probability</text><text transform="translate(12 ${(top+h-bottom)/2}) rotate(-90)" text-anchor="middle" font-size="10" fill="#68717d">Observed win rate</text></svg>`;
    $('calibration-chart').innerHTML=svg;
  }

  document.querySelectorAll('[data-role]').forEach(b=>b.addEventListener('click',()=>setRole(b.dataset.role)));
  document.querySelector('.role-tabs').addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();setRole(state.role==='batters'?'bowlers':'batters');$(`tab-${state.role}`).focus();}});
  $('player-search').addEventListener('input',e=>{state.search=e.target.value;renderPlayers();});
  [['pool-filter','pool'],['role-filter','group'],['coverage-filter','coverage'],['sort-filter','sort']].forEach(([id,key])=>$(id).addEventListener('change',e=>{state[key]=e.target.value;renderPlayers();}));
  $('view-table').addEventListener('click',()=>{state.view='table';renderPlayers();});$('view-chart').addEventListener('click',()=>{state.view='chart';renderPlayers();});
  $('reset-filters').addEventListener('click',()=>{state.search='';state.group='all';state.coverage='all';$('player-search').value='';$('role-filter').value='all';$('coverage-filter').value='all';renderPlayers();});
  $('copy-rankings').addEventListener('click',()=>copy(selected(state.role).map(p=>`${p.rank}. ${p.name}`).join('\n'),`Final top 10 ${state.role} copied in submission order`));
  document.addEventListener('click',e=>{const b=e.target.closest('[data-profile]');if(b)openProfile(b.dataset.profileRole||state.role,b.dataset.profile);});
  document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('g[data-profile]')){e.preventDefault();openProfile(state.role,e.target.dataset.profile);}if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)&&!$('player-dialog').open){e.preventDefault();$('player-search').focus();}});
  $('player-rows').addEventListener('change',e=>{if(e.target.matches('[data-compare]'))toggleCompare(state.role,e.target.dataset.compare);});
  $('compare-tray-clear').addEventListener('click',()=>{state.compare.clear();renderTray();renderPlayers();});
  $('compare-tray-open').addEventListener('click',()=>{setupComparison(state.role,[...state.compare]);$('compare').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});state.compare.clear();renderTray();renderPlayers();});
  $('compare-role').addEventListener('change',e=>setupComparison(e.target.value));$('compare-a').addEventListener('change',renderComparison);$('compare-b').addEventListener('change',renderComparison);
  $('dialog-close').addEventListener('click',()=>$('player-dialog').close());$('player-dialog').addEventListener('close',closeProfile);
  $('player-dialog').addEventListener('click',e=>{if(e.target===$('player-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
  renderHero();renderCoverage();renderValidation();setupComparison('batters');roleOptions();
  const params=new URLSearchParams(location.search);setRole(params.get('role')==='bowlers'?'bowlers':'batters');
  if(params.has('player'))openProfile(state.role,params.get('player'),false);
})();
