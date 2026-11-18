/* Run only in the generated local QA harness, never included in the delivered site. */
(async()=>{
  let checks=0;
  const $=id=>document.getElementById(id);
  const assert=(condition,message)=>{if(!condition)throw new Error(message);checks++;};
  const change=(id,value)=>{$(id).value=value;$(id).dispatchEvent(new Event('change',{bubbles:true}));};
  const search=value=>{$('player-search').value=value;$('player-search').dispatchEvent(new Event('input',{bubbles:true}));};
  const rows=()=>document.querySelectorAll('#player-rows tr');
  try{
    const portalLists = [...document.querySelectorAll('#portal-lists article')];
    assert(portalLists.length===2&&portalLists.every(list=>list.querySelectorAll('tbody tr').length===10),'Both Unstop lists contain ten ranks');
    assert(portalLists[0].querySelector('tbody tr').textContent.includes('Dinesh Karthik')&&portalLists[1].querySelector('tbody tr').textContent.includes('Ravindra Jadeja'),'Unstop lists show the team leaders');
    assert($('backtest-table').querySelectorAll('tbody tr').length===6&&$('backtest-context').textContent.includes('ten training-eligible'),'Full backtest shows both roles for three seasons');
    change('backtest-pool','portal_roles');
    assert($('backtest-context').textContent.includes('20 Unstop names')&&$('backtest-table').textContent.includes('2/2 scored'),'Backtest pool switches to the restricted replay');
    change('backtest-pool','roles');

    assert(rows().length===10&&rows()[0].textContent.includes('Ashutosh Sharma'),'Default final batting order');
    assert($('cutline-summary').textContent.includes('Kamindu Mendis (12.44)')&&$('cutline-summary').textContent.includes('Yashasvi Jaiswal (12.17)'),'Batting cutoff names and scores');
    change('pool-filter','all');assert(rows().length===176,'All eligible batting entries');
    search('Tim David');assert(rows().length===1&&rows()[0].dataset.player==='6396','Player search');
    search('zz_no_such_player');assert(!$('empty-state').hidden&&rows().length===0,'Empty search state');
    $('reset-filters').click();assert(rows().length===176&&$('player-search').value==='','Reset search and filters');
    change('pool-filter','selected');change('role-filter','Opening');assert(rows().length===3,'Observed opening roles');
    let copied='';
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{copied=text;}}});
    document.querySelector('[data-portal-copy="bowlers"]').click();await new Promise(r=>setTimeout(r,10));
    assert(copied.split('\n').length===10&&copied.startsWith('1. Ravindra Jadeja')&&copied.endsWith('10. Muhammad Farooq'),'Copy uses the exact Unstop dropdown order');
    $('copy-rankings').click();await new Promise(r=>setTimeout(r,10));
    assert(copied.split('\n').length===10&&copied.startsWith('1. Ashutosh Sharma')&&copied.endsWith('10. Kamindu Mendis'),'Copy preserves full submission order despite filters');
    change('role-filter','all');$('view-chart').click();assert(!$('chart-view').hidden&&document.querySelectorAll('.chart-player').length===10,'Uncertainty plot');
    document.querySelector('.chart-player').dispatchEvent(new MouseEvent('click',{bubbles:true}));
    assert($('player-dialog').open&&$('player-title').textContent==='Ashutosh Sharma'&&$('player-profile').textContent.includes('112'),'Open plot player profile');
    $('profile-copy-link').click();await new Promise(r=>setTimeout(r,10));
    const profileUrl=new URL(copied);
    assert(profileUrl.origin===location.origin&&profileUrl.searchParams.get('role')==='batters'&&profileUrl.searchParams.get('player')==='8101','Profile link uses the current deployment domain');
    $('dialog-close').click();assert(!$('player-dialog').open,'Close profile');
    $('view-table').focus();$('view-table').click();document.querySelector('[data-profile="6396"]').click();$('profile-add-compare').click();
    assert(!$('compare-tray').hidden&&$('compare-tray-open').disabled,'Single comparison selection');
    document.querySelector('[data-compare="8101"]').click();assert(!$('compare-tray-open').disabled,'Two-player comparison enabled');
    $('compare-tray-open').click();
    assert($('compare-a').value==='6396'&&$('compare-b').value==='8101'&&document.querySelectorAll('.compare-card').length===2,'Comparison shows selected players');
    $('tab-bowlers').click();assert(rows().length===10&&rows()[0].textContent.includes('Joshua Little'),'Final bowling order');
    assert($('cutline-summary').textContent.includes('Sufiyan Muqeem (7.84)')&&$('cutline-summary').textContent.includes('Rashid Khan (7.68)'),'Bowling cutoff updates when the discipline changes');
    $('compare-cutline').click();
    assert($('compare-role').value==='bowlers'&&[...document.querySelectorAll('.compare-card h3')].map(node=>node.textContent).join(', ')==='Sufiyan Muqeem, Rashid Khan','Cutoff comparison includes the eligible player outside the top 10');
    change('role-filter','Powerplay');assert(rows().length===4,'Powerplay role filter');
    change('role-filter','all');change('coverage-filter','t20i');assert(rows().length===4&&[...rows()].some(r=>r.textContent.includes('Shaheen Afridi')),'Evidence coverage filter');
    change('coverage-filter','all');change('sort-filter','name');assert(rows()[0].textContent.includes('Hasan Mahmud')&&rows()[0].querySelector('.rank-number').textContent==='09','Sorting retains official ranks');
    change('compare-role','batters');change('compare-role','bowlers');assert(document.querySelector('.compare-card h3').textContent==='Joshua Little','Discipline-specific comparison');
    change('sort-filter','score');$('tab-batters').click();change('compare-role','batters');window.scrollTo(0,0);
    await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
    assert(document.documentElement.scrollWidth<=window.innerWidth+1,'No document-level horizontal overflow');
    $('toast').classList.remove('show');
    document.body.dataset.qa='passed';console.log('UI_CHECKS_PASSED:'+checks);
  }catch(error){document.body.dataset.qa='failed';console.error('UI_CHECK_FAILED:'+error.message);throw error;}
})();
