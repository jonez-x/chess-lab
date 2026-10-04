'use strict';
(() => {
  const root = document.getElementById('chess-studio-v1');
  const $ = s => root.querySelector(s);
  let state = null, selected = null, busy = false, polling = false, setup = false, step = 0, draft = {}, flipped = false, lastFen = null;
  const names = {p:'Bauer', n:'Springer', b:'Läufer', r:'Turm', q:'Dame', k:'König'};
  const sounds = new ChessSounds();
  let arrows=[], drawMode=false, arrowStart=null, drag=null, suppressClick=false, lastPosition=null, moveAnimation=null;
  let coachDraft='', coachDraftKey='', visualKey='', visualIndex=0, visualHidden=false, coachUiKey='', noteDraft='';
  function visualScene(){
    const g=state.game,c=g?.coach,key=g?.id+':'+g?.fen+':'+c?.stage;
    if(key!==visualKey){visualKey=key;visualIndex=0;visualHidden=false;}
    return visualHidden?null:c?.visuals?.[visualIndex];
  }
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const button = (action, label, primary=false, disabled=false) => `<button type="button" class="cs-button ${primary?'cs-primary':''}" data-action="${action}" ${disabled?'disabled':''}>${label}</button>`;
  const iconButton = (action, icon, label, extra='') => `<button type="button" class="tool-button" data-action="${action}" aria-label="${label}" title="${label}" ${extra}><i data-lucide="${icon}" aria-hidden="true"></i></button>`;
  const piece = (p, extra='', style='') => `<span class="cs-piece ${extra}"${style} aria-hidden="true"><img src="/pieces/cburnett/${p===p.toUpperCase()?'w':'b'}${p.toUpperCase()}.svg" alt="" draggable="false"></span>`;
  function paintIcons(){ lucide.createIcons({attrs:{width:20,height:20}}); }
  function notice(message=''){ $('#notice').textContent=message; $('#notice').hidden=!message; }
  function modal(html){ $('#modal-content').innerHTML=html; $('#modal').showModal(); paintIcons(); }
  function closeModal(){ $('#modal').close(); }
  function accept(next, silent=false){
    if(state && next.revision<state.revision)return;
    const old=state?.game,g=next.game;
    if(!silent && next.profile.sound!==false && old && g && old.id===g.id && g.moves.length>old.moves.length && g.moves.length-old.moves.length<=2 && old.moves.every((m,i)=>m.uci===g.moves[i].uci)){
      g.moves.slice(old.moves.length).forEach((m,i)=>sounds.play(m.capture,i*.14));
    }
    if(!silent && old && g && old.id===g.id && g.moves.length>old.moves.length && old.moves.every((m,i)=>m.uci===g.moves[i].uci)){
      const latest=g.moves[g.moves.length-1];
      moveAnimation={uci:latest.uci,capture:Boolean(latest.capture),token:Date.now()};
    }
    state=next;render();
  }
  async function command(action, data={}){
    if(busy) return false;
    busy=true; $('#save-status').textContent='Wird gespeichert …'; root.classList.add('is-busy'); notice();
    try{
      for(let attempt=0;attempt<2;attempt++){
        const response=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Schachcoach':'1'},body:JSON.stringify({action,revision:state.revision,...data})});
        const result=await response.json();
        if(response.ok){accept(result,['new','resume','example','undo','retry'].includes(action));return true;}
        // A background evaluation can advance the revision between selecting
        // and releasing a piece. Refresh once and transparently retry the
        // same intentional action so a harmless analysis update cannot eat it.
        if(response.status===409&&result.state&&attempt===0){accept(result.state);continue;}
        if(result.state)accept(result.state);
        throw new Error(result.error || 'Änderung fehlgeschlagen.');
      }
    }catch(e){notice(e.message==='Failed to fetch'?'Die lokale App ist nicht erreichbar. Öffne Start.command erneut.':e.message); $('#save-status').textContent='Nicht gespeichert'; return false;}
    finally{busy=false;root.classList.remove('is-busy');}
  }
  async function refresh(){
    if(busy||polling)return;
    polling=true;
    try{
      const response=await fetch('/api/state'); if(!response.ok)throw new Error(); const data=await response.json();
      if(!state){state=data;setup=!data.game;draft={...data.profile};render();}
      else if(data.revision!==state.revision)accept(data);
      if($('#save-status').textContent==='Verbindung unterbrochen')$('#save-status').textContent='Lokal gespeichert';
    }catch(e){$('#save-status').textContent='Verbindung unterbrochen';if(!state){$('#loading').innerHTML='<h2>Die App ist nicht erreichbar.</h2><p>Starte Chess Lab über Start.command. Diese Seite verbindet sich automatisch erneut.</p>';}}
    finally{polling=false;}
  }
  function choices(key,items){return `<div class="cs-choices">${items.map(([v,title,sub])=>`<button type="button" class="cs-choice" data-choice="${key}" data-value="${v}" aria-pressed="${draft[key]===v}"><span><strong>${title}</strong><small>${sub}</small></span><span class="cs-radio" aria-hidden="true"></span></button>`).join('')}</div>`;}
  function renderSetup(){
    $('#step-title').textContent=['01 / Ankommen','02 / Dein Coach','03 / Dein Gegenüber'][step];
    root.querySelectorAll('.cs-dots span').forEach((el,i)=>el.classList.toggle('cs-active',i===step));
    let html='';
    if(step===0)html='<h3>Wo stehst du gerade?</h3><p>Dein Coach erklärt so, dass du gut mitkommst.</p>'+choices('level',[['beginner','Ich lerne noch','Regeln bekannt, Ideen noch neu.'],['returning','Ich spiele gelegentlich','Die Grundlagen sitzen.'],['confident','Ich spiele regelmäßig','Ich möchte mein Denken schärfen.']]);
    if(step===1)html='<h3>Ein Impuls.<br>Wenn er dir hilft.</h3><div class="cs-explain-row"><span>1</span><div><strong>Erst selbst denken</strong><p>Der Coach spricht einzelne Angriffe an. Zuerst stellt er eine Frage.</p></div></div><div class="cs-explain-row"><span>2</span><div><strong>So viel Hilfe wie nötig</strong><p>Weitere Hinweise und die Lösung gibt es auf deinen Wunsch.</p></div></div><div class="cs-explain-row"><span>3</span><div><strong>Du kannst immer weiterspielen</strong><p>Überspringen beendet den Lernmoment. Deine Partien werden automatisch lokal gespeichert.</p></div></div>';
    if(step===2)html='<h3>Wie viel Gegenwind?</h3><p>Spielstärke und Lernniveau sind getrennt.</p>'+choices('bot',[['Leicht','Leicht','Mehr Raum zum Ausprobieren.'],['Mittel','Mittel','Eine konzentrierte Trainingspartie.'],['Anspruchsvoll','Anspruchsvoll','Weniger Fehler, mehr Widerstand.']])+`<div class="color-choice" role="group" aria-label="Deine Farbe"><button class="cs-button" data-choice="color" data-value="white" aria-pressed="${draft.color==='white'}">Ich spiele Weiß</button><button class="cs-button" data-choice="color" data-value="black" aria-pressed="${draft.color==='black'}">Ich spiele Schwarz</button></div>`;
    $('#setup-content').innerHTML=html;
    $('#setup-actions').innerHTML=button(step===2?'start':'setup-next',step===2?'Training beginnen →':'Weiter →',true)+(step?button('setup-back','Zurück'):'')+(state.game?'<button class="cs-help-link" data-action="setup-cancel">Zur Partie</button>':'');
    $('#intro-pieces').innerHTML=['P','R','N','B','Q','K'].map(piece).join('');
  }
  function order(){const black=(state.game.color==='black')!==flipped;return {files:black?'hgfedcba':'abcdefgh',ranks:black?[1,2,3,4,5,6,7,8]:[8,7,6,5,4,3,2,1]};}
  function renderBoard(){
    const g=state.game,{files,ranks}=order(),visual=visualScene();
    $('#ranks').innerHTML=ranks.map(r=>`<span>${r}</span>`).join(''); $('#files').innerHTML=[...files].map(f=>`<span>${f}</span>`).join('');
    const legal=g.legal_moves.filter(m=>m.slice(0,2)===selected), last=g.moves.at(-1)?.uci;
    const latest=g.moves.at(-1)?.uci;
    const animated=moveAnimation&&moveAnimation.uci===latest?moveAnimation:null;
    const destination=animated?.uci.slice(2,4);
    const source=animated?.uci.slice(0,2);
    const fromIndex=source?files.indexOf(source[0]):0;
    const toIndex=destination?files.indexOf(destination[0]):0;
    const fromRank=source?ranks.indexOf(Number(source[1])):0;
    const toRank=destination?ranks.indexOf(Number(destination[1])):0;
    let html='';
    for(const rank of ranks)for(const file of files){
      const sq=file+rank,p=g.pieces[sq],target=legal.some(m=>m.slice(2,4)===sq),mark=!visualHidden&&(visual?.marks||g.coach?.marks||[]).includes(sq);
      const capture=target&&(g.capture_moves||[]).some(m=>m.slice(0,2)===selected&&m.slice(2,4)===sq);
      const isLast=last&&(last.slice(0,2)===sq||last.slice(2,4)===sq);
      const arriving=animated&&sq===destination;
      const moveX=arriving?(fromIndex-toIndex)*114:0;
      const moveY=arriving?(fromRank-toRank)*114:0;
      const arrivalClass=arriving?'cs-piece-arriving':'';
      const arrivalStyle=arriving?` style="--move-x:${moveX}%;--move-y:${moveY}%"`:'';
      const captureArrival=arriving&&animated.capture?'cs-capture-arrival':'';
      html+=`<button type="button" class="cs-square ${('abcdefgh'.indexOf(file)+rank)%2===1?'cs-dark':''} ${selected===sq?'cs-selected':''} ${mark?'cs-coach-focus':''} ${target?(capture?'cs-capture':'cs-target'):''} ${captureArrival} ${isLast?'cs-last':''} ${g.check===sq?'cs-check':''}" data-square="${sq}" aria-label="${sq}${p?', '+(p===p.toUpperCase()?'Weiß ':'Schwarz ')+names[p.toLowerCase()]:', leer'}${target?(capture?', möglicher Schlagzug':', möglicher Zug'):''}${g.check===sq?', Schach':''}" aria-pressed="${selected===sq}">${p?piece(p,arrivalClass,arrivalStyle):''}</button>`;
    }
    html+='<div class="annotation-layer" id="annotation-layer"></div>';
    $('#board').innerHTML=html;
    renderAnnotations();
    if(animated){
      const token=animated.token;
      window.setTimeout(()=>{
        if(moveAnimation?.token===token){moveAnimation=null;renderBoard();}
      },540);
    }
  }
  function arrowLayer(list,owner){
    if(!list.length)return '';
    const {files,ranks}=order(),xy=s=>[(files.indexOf(s[0])+.5)*100,(ranks.indexOf(Number(s[1]))+.5)*100];
    let html=`<svg class="cs-overlay ${owner}-arrows" viewBox="0 0 800 800" aria-hidden="true">`;
    for(const a of list){
      if(!/^[a-h][1-8]$/.test(a.from)||!/^[a-h][1-8]$/.test(a.to)||a.from===a.to)continue;
      const [x,y]=xy(a.from),[xx,yy]=xy(a.to),dx=xx-x,dy=yy-y,len=Math.hypot(dx,dy);
      // One silhouette keeps the shaft and tip seamless at every angle.
      // Dimensions are relative to a 100-unit square, independent of length.
      const tip=len-16, neck=tip-24, angle=Math.atan2(dy,dx)*180/Math.PI;
      const path=`M 20 -5 L ${neck} -5 L ${neck} -14 Q ${neck} -16 ${neck+2} -14 L ${tip} -1 Q ${tip+2} 0 ${tip} 1 L ${neck+2} 14 Q ${neck} 16 ${neck} 14 L ${neck} 5 L 20 5 A 5 5 0 0 1 20 -5 Z`;
      html+=`<g class="board-arrow" data-arrow-from="${a.from}" data-arrow-to="${a.to}" data-owner="${owner}" transform="translate(${x} ${y}) rotate(${angle})"><path d="${path}"/></g>`;
    }
    return html+'</svg>';
  }
  function renderAnnotations(){
    const layer=$('#annotation-layer');if(!layer)return;
    const coach=visualHidden?[]:(visualScene()?.arrows||state.game.coach?.arrows||[]);
    const preview=drag&&drag.to&&drag.from!==drag.to?[{from:drag.from,to:drag.to}]:[];
    layer.innerHTML=arrowLayer(coach,'coach')+arrowLayer(arrows,'user')+arrowLayer(preview,'preview')+(coach.length?'<span class="cs-board-note">'+esc(coach[0].label)+'</span>':'');
    $('[data-action="draw"]').setAttribute('aria-pressed',String(drawMode));
    $('[data-action="clear-arrows"]').disabled=!arrows.length&&!arrowStart;
    $('#drawing-help').textContent=drawMode?(arrowStart?'Jetzt das Zielfeld wählen':'Start- und Zielfeld wählen oder ziehen'):'Rechtsziehen für einen Pfeil';
    $('#board').classList.toggle('is-drawing',drawMode);
    $('#board').querySelectorAll('[data-square]').forEach(el=>el.classList.toggle('arrow-start',el.dataset.square===arrowStart));
  }
  function toggleArrow(from,to){
    if(from===to)return;
    const index=arrows.findIndex(a=>a.from===from&&a.to===to);
    if(index>=0)arrows.splice(index,1);else if(arrows.length<24)arrows.push({from,to});
    $('#drawing-status').textContent=`${arrows.length} eigene Pfeile. ${index>=0?'Entfernt':'Gezeichnet'}: ${from} nach ${to}.`;
    arrowStart=null;renderAnnotations();
  }
  function renderCoach(){
    const g=state.game,c=g.coach,key=g.id+':'+g.fen+':'+c?.stage;
    const same=key===coachUiKey;
    const opened=same?[...$('#coach-content').querySelectorAll('details[open]')].map(el=>el.className):[];
    const oldTranscript=$('.coach-transcript');
    const scrollTop=same?oldTranscript?.scrollTop:0;
    const atBottom=!same||!oldTranscript||oldTranscript.scrollHeight-oldTranscript.clientHeight-oldTranscript.scrollTop<36;
    const focused=document.activeElement?.id;
    const selection=focused==='coach-question'?[document.activeElement.selectionStart,document.activeElement.selectionEnd]:null;
    if(!same){noteDraft='';coachUiKey=key;}
    let body='',actions='';
    if(g.result){
      body=`<div class="coach-empty"><span class="cs-step-label">${esc(g.result.score)}</span><h3>${esc(g.result.reason)}</h3><p>Deine Partie ist gespeichert.</p></div>`;
      actions=button('history','Partien')+button('new-menu','Neue Partie',true);
    }else if(g.error){
      body='<div class="coach-empty"><h3>Kurze Pause.</h3><p>'+esc(g.error)+'</p></div>';
      actions=button('retry_engine','Erneut versuchen',true);
      if(g.turn===g.color)actions+=button('hint','Hinweis anfordern');
    }else if(g.pending){
      body=`<div class="coach-empty"><p role="status">${g.pending==='bot'?'Der Gegner denkt …':'Die Stellung wird analysiert …'}</p></div>`;
      if(g.pending==='hint')actions=button('skip','Weiterspielen');
    }else if(c){
      const intro=c.dialogue_intro||c;
      if(key!==coachDraftKey){coachDraft='';coachDraftKey=key;}
      body=`<section class="coach-dialogue" aria-label="Gespräch mit dem Coach"><div class="coach-transcript" role="log" aria-label="Coach-Gespräch" aria-live="polite"><article class="coach-message from-coach lesson-message"><span class="message-topic">${esc(c.concept)} · Hinweis ${intro.stage+1}/3</span><p>${esc(intro.text)}</p></article>`;
      for(const m of c.dialogue||[])body+=`<article class="coach-message ${m.role==='user'?'from-player':'from-coach'}" aria-label="${m.role==='user'?'Du':'Coach'}"><span class="cs-sr">${m.role==='user'?'Du':'Coach'}</span><p>${esc(m.text)}</p></article>`;
      if(c.llm_pending)body+='<p class="typing-indicator" role="status">Coach schreibt …</p>';
      if(c.llm_error)body+=`<p class="chat-error" role="status">${esc(c.llm_error)}</p>`;
      body+='</div></section>';
      if(c.visuals?.length){
        const v=visualScene(),current=c.visuals[visualIndex];
        body+=`<section class="visual-coach" aria-label="Visueller Coach"><div class="visual-picker"><label class="cs-sr" for="visual-scene">Bretthinweis wählen</label><select id="visual-scene" title="Bretthinweis wählen">${c.visuals.map((v,i)=>`<option value="${i}" ${i===visualIndex?'selected':''}>${esc(v.title)}</option>`).join('')}</select><span class="visual-count" aria-label="Hinweis ${visualIndex+1} von ${c.visuals.length}">${visualIndex+1}/${c.visuals.length}</span>${iconButton('visual-prev','chevron-left','Vorheriger Bretthinweis',visualIndex===0?'disabled':'')}${iconButton('visual-next','chevron-right','Nächster Bretthinweis',visualIndex===c.visuals.length-1?'disabled':'')}${iconButton('toggle-visual',visualHidden?'eye-off':'eye',visualHidden?'Bretthinweis einblenden':'Bretthinweis ausblenden',`aria-pressed="${!visualHidden}"`)}</div><details class="visual-details"><summary>Erklärung am Brett</summary><p>${esc((v||current).text)}</p></details></section>`;
      }
      if(state.local_coach){
        body+=`<form id="coach-chat-form"><label class="cs-sr" for="coach-question">Deine Frage oder Idee</label><textarea id="coach-question" maxlength="1000" rows="2" placeholder="Deine Frage oder Idee …" ${c.llm_pending?'disabled':''}>${esc(coachDraft)}</textarea><button type="submit" class="send-button" aria-label="An Coach senden" title="Senden · Enter (neue Zeile: Shift+Enter)" ${c.llm_pending?'disabled':''}><i data-lucide="arrow-up" aria-hidden="true"></i></button></form>`;
      }
      body+=`<details class="reflection"><summary>Notiz${c.note?' gespeichert':''}</summary>${c.note?`<p>${esc(c.note)}</p>`:`<label class="cs-sr" for="reflection">Eigene Notiz</label><textarea id="reflection" maxlength="1000" rows="2" placeholder="Dein Gedanke zur Stellung …">${esc(noteDraft)}</textarea><button class="cs-textbutton" data-action="note">Speichern</button>`}</details>`;
      if(c.stage<2)actions=button('next',c.stage===0?'Mehr Hilfe':'Zug zeigen');
      if(c.can_retry)actions+=iconButton('retry','rotate-ccw','Noch einmal überlegen');
      actions+=button('skip','Weiterspielen',true);
    }else{
      body='<div class="coach-empty"><h3>Was möchtest du verstehen?</h3><p>Hol dir einen Hinweis zur Stellung und besprich deine Idee mit dem Coach.</p></div>';
      if(g.check)body+='<p>Dein König steht im Schach.</p>';
      actions=button('hint','Gespräch starten',true,g.turn!==g.color);
    }
    $('#coach-content').innerHTML=body;$('#coach-actions').innerHTML=actions;
    $('#coach-content').querySelectorAll('details').forEach(el=>{el.open=opened.includes(el.className);});
    paintIcons();
    const transcript=$('.coach-transcript');
    if(transcript)transcript.scrollTop=atBottom?transcript.scrollHeight:scrollTop||0;
    if(selection&&$('#coach-question')&&!$('#coach-question').disabled){$('#coach-question').focus({preventScroll:true});$('#coach-question').setSelectionRange(...selection);}
  }
  function showMoves(){
    const rows=new Map();for(const m of state.game.moves){if(!rows.has(m.number))rows.set(m.number,{});rows.get(m.number)[m.color]=m.san;}
    modal('<h2 id="modal-title">Zugverlauf</h2><div class="move-scroll">'+([...rows].map(([n,m])=>`<div class="cs-move-row"><span>${n}.</span><span>${esc(m.white||'…')}</span><span>${esc(m.black||'…')}</span></div>`).join('')||'<p>Noch keine Züge.</p>')+'</div>');
    const scroll=$('.move-scroll');scroll.scrollTop=scroll.scrollHeight;
  }
  function renderAdvantage(){
    const strip=$('#advantage-strip'), buttonEl=$('[data-action="toggle-advantage"]'), g=state?.game;
    if(!strip||!buttonEl)return;
    const visible=state.profile.show_advantage!==false;
    strip.hidden=!visible||!g;
    buttonEl.setAttribute('aria-pressed',String(visible));
    buttonEl.setAttribute('aria-label',visible?'Vorteil ausblenden':'Vorteil einblenden');
    buttonEl.title=buttonEl.getAttribute('aria-label');
    if(!visible||!g)return;
    const value=$('#advantage-value'), marker=$('#advantage-marker'), evaluation=g.evaluation;
    const blackAtBottom=(g.color==='black')!==flipped;
    const scale=root.querySelectorAll('.advantage-scale span');
    scale[0].textContent=blackAtBottom?'Weiß':'Schwarz';
    scale[2].textContent=blackAtBottom?'Schwarz':'Weiß';
    $('.advantage-track').setAttribute('aria-label',`Vorteil: oben ${scale[0].textContent}, unten ${scale[2].textContent}`);
    strip.classList.remove('is-white','is-black','is-even','is-pending');
    if(g.evaluation_pending){
      strip.classList.add('is-pending');value.textContent='…';value.title='Wird berechnet';marker.style.top='50%';
      $('.advantage-track').setAttribute('aria-valuenow','50');return;
    }
    if(!evaluation){
      strip.classList.add('is-even');value.textContent='–';value.title='Noch keine Bewertung';marker.style.top='50%';
      $('.advantage-track').setAttribute('aria-valuenow','50');return;
    }
    const mate=evaluation.mate;
    const cp=typeof evaluation.cp==='number'?evaluation.cp:0;
    const normalized=Math.max(4,Math.min(96,50+(mate?Math.sign(mate)*42:(cp/100)*15)));
    marker.style.top=(blackAtBottom?100-normalized:normalized)+'%';$('.advantage-track').setAttribute('aria-valuenow',String(Math.round(normalized)));
    if(mate){
      const side=mate>0?'Weiß':'Schwarz';value.textContent=`M${Math.abs(mate)}`;value.title=`${side} setzt matt in ${Math.abs(mate)}`;strip.classList.add(mate>0?'is-white':'is-black');return;
    }
    const pawns=Math.abs(cp)/100;
    if(pawns<0.08){value.textContent='0,0';value.title='Ausgeglichen';strip.classList.add('is-even');}
    else {const side=cp>0?'Weiß':'Schwarz';value.textContent=`+${pawns.toFixed(1).replace('.',',')}`;value.title=`${side} +${pawns.toFixed(2).replace('.',',')}`;strip.classList.add(cp>0?'is-white':'is-black');}
  }
  function renderMaterial(){
    const g=state.game,m=g.material,panel=$('#material-panel');
    if(!m){panel.innerHTML='';return;}
    const opponent=g.color==='white'?'black':'white',difference=m.totals[g.color]-m.totals[opponent];
    const icons=list=>list.map(p=>`<img src="/pieces/cburnett/${p===p.toUpperCase()?'w':'b'}${p.toUpperCase()}.svg" alt="${p===p.toUpperCase()?'Weißer':'Schwarzer'} ${names[p.toLowerCase()]}">`).join('');
    panel.innerHTML=[[opponent,'Gegner',-difference],[g.color,'Du',difference]].map(([color,label,lead])=>`<div class="material-row" title="${label==='Du'?'Von dir':'Vom Gegner'} geschlagene Figuren"><span>${label}</span><div class="captured-pieces" aria-label="${label==='Du'?'Von dir':'Vom Gegner'} geschlagen${m.captured[color].length?'':': noch keine Figuren'}">${icons(m.captured[color])}</div>${lead>0?`<strong class="material-lead" title="${lead} Punkte Materialvorteil" aria-label="${lead} Punkte Materialvorteil">+${lead}</strong>`:''}</div>`).join('');
  }
  function render(){
    if(!state)return;
    const g=state.game;
    const position=g?g.id+':'+g.fen:null;
    if(position!==lastPosition){selected=null;arrows=[];arrowStart=null;drag=null;lastPosition=position;}
    lastFen=g?.fen;
    root.style.colorScheme=state.profile.theme;document.documentElement.style.colorScheme=state.profile.theme;
    root.querySelectorAll('[data-theme]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.theme===state.profile.theme)));
    $('#loading').hidden=true;$('#onboarding').hidden=!setup;$('#game').hidden=setup||!g;
    $('#save-status').textContent='Lokal gespeichert';
    if(setup)renderSetup();
    if(g&&!setup){
      $('#bot-label').textContent=g.bot;
      $('#player-label').textContent=state.profile.name+' / '+(g.color==='white'?'Weiß':'Schwarz');
      $('#human-stone').classList.toggle('cs-hollow',g.color==='white');$('#opponent-stone').classList.toggle('cs-hollow',g.color==='black');
      $('#turn-label').textContent=g.result?'Partie beendet':g.coach?.kind==='after'?'Partie pausiert':g.pending==='hint'?'Coach denkt …':g.turn===g.color?'Du bist am Zug':'Trainingspartner denkt …';
      $('#game-caption').textContent=g.example?'Sizilianisch · Trainingsstellung':'Dein nächster Gedanke.';
      $('#claim-draw').hidden=!g.can_claim_draw;
      $('[data-action="undo"]').disabled=!g.moves.length;
      renderBoard();renderCoach();
      renderAdvantage();
      renderMaterial();
    }
    paintIcons();
  }
  async function square(sq){
    if(suppressClick){suppressClick=false;return;}
    if(drawMode){if(arrowStart){toggleArrow(arrowStart,sq);arrowStart=null;}else arrowStart=sq;renderAnnotations();return;}
    if(busy||!state.game.legal_moves.length)return;
    const g=state.game;
    if(selected){
      const moves=g.legal_moves.filter(m=>m.slice(0,2)===selected&&m.slice(2,4)===sq);
      if(moves.length>1){modal('<h2 id="modal-title">Dein Bauer wird …</h2><p>Wähle eine Figur für die Umwandlung.</p><div class="promotion-options">'+moves.map(m=>`<button class="cs-button" data-promotion="${m}">${names[m[4]]}</button>`).join('')+'</div>');return;}
      if(moves.length===1){selected=null;await command('move',{move:moves[0]});return;}
    }
    selected=selected===sq?null:g.legal_moves.some(m=>m.slice(0,2)===sq)?sq:null;
    renderBoard();paintIcons();$(`[data-square="${sq}"]`)?.focus({preventScroll:true});
  }
  function newMenu(){modal('<span class="cs-kicker cs-muted">Dein Training</span><h2 id="modal-title">Ein neuer Gedanke.</h2><p>Deine aktuelle Partie bleibt gespeichert und lässt sich unter „Mein Training“ fortsetzen.</p><div class="modal-actions">'+button('new-setup','Neue Partie',true)+button('example','Sizilianisch ausprobieren')+'</div><p class="small cs-muted">Die Trainingsstellung beginnt nach e4 c5, Sf3 Sc6, d4 d6. Weiß ist am Zug.</p>');}
  async function history(){
    try{
      const response=await fetch('/api/history');if(!response.ok)throw new Error();const h=await response.json();
      const labels={offered:'Lernmoment angeboten',skipped:'Übersprungen',hint_shown:'Hinweis angesehen',solution_shown:'Erklärung angesehen',move_after_help:'Zug mit vorheriger Hilfe',reflection:'Eigene Idee festgehalten',retry:'Erneut überlegt',interrupted:'Unterbrochen'};
      const events=h.events.filter(e=>e.outcome!=='offered').slice(0,12);
      modal('<span class="cs-kicker cs-muted">Lokal & persönlich</span><h2 id="modal-title">Dein Training.</h2><h3>Partien</h3><div class="history-list">'+(h.games.map(g=>`<button class="history-game" data-resume="${esc(g.id)}"><span>${g.example?'Sizilianisch':'Trainingspartie'}<small>${new Date(g.created).toLocaleDateString('de-DE')} · ${esc(g.bot)} · ${g.moves} Halbzüge</small></span><span>${esc(g.result?.score||'Fortsetzen →')}</span></button>`).join('')||'<p>Noch keine Partie.</p>')+'</div><h3>Deine Lernmomente</h3><p class="small cs-muted">Beobachtungen, keine Bewertung deines Könnens.</p><div class="history-list">'+(events.map(e=>`<div class="history-event"><strong>${esc(e.concept_label)}</strong><span>${esc(labels[e.outcome]||e.outcome)} · Stufe ${e.stage+1}</span>${e.reflection?`<p>${esc(e.reflection)}</p>`:''}</div>`).join('')||'<p class="cs-muted">Hier erscheinen deine Hinweise und Gedanken.</p>')+'</div><a class="cs-button" href="/api/export/backup" download>Sicherung herunterladen</a>');
    }catch(e){notice('Die Trainingshistorie konnte nicht geladen werden.');}
  }
  function settings(){
    const p=state.profile;
    modal(`<span class="cs-kicker cs-muted">Dein Raum</span><h2 id="modal-title">So lernst du.</h2><form id="settings-form"><label>Name<input name="name" maxlength="40" value="${esc(p.name)}"></label><label>Lernniveau<select name="level"><option value="beginner" ${p.level==='beginner'?'selected':''}>Ich lerne noch</option><option value="returning" ${p.level==='returning'?'selected':''}>Ich spiele gelegentlich</option><option value="confident" ${p.level==='confident'?'selected':''}>Ich spiele regelmäßig</option></select></label><label class="checkbox-label"><input type="checkbox" name="auto_coach" ${p.auto_coach?'checked':''}>Coach darf mich unterbrechen</label><p class="small cs-muted">Jeder Lernmoment bleibt überspringbar. Automatisch höchstens einmal in fünf eigenen Zügen.</p><label class="checkbox-label"><input type="checkbox" name="show_advantage" ${p.show_advantage!==false?'checked':''}>Vorteilsleiste anzeigen</label><label class="checkbox-label"><input type="checkbox" name="sound" ${p.sound!==false?'checked':''}>Zug- und Schlaggeräusche</label><button type="button" class="cs-textbutton" data-action="preview-sound">Klänge anhören</button><button type="submit" class="cs-button cs-primary">Speichern</button></form><div class="modal-actions">${button('onboard-again','Einführung ansehen')}${state.game&&!state.game.result?button('resign-menu','Partie aufgeben'):''}</div>`);
  }
  root.addEventListener('click',async e=>{
    const b=e.target.closest('button');if(!b||b.disabled||busy)return;
    if(b.dataset.square)return square(b.dataset.square);
    if(b.dataset.theme)return command('settings',{settings:{theme:b.dataset.theme}});
    if(b.dataset.choice){draft[b.dataset.choice]=b.dataset.value;renderSetup();paintIcons();return;}
    if(b.dataset.promotion){closeModal();selected=null;return command('move',{move:b.dataset.promotion});}
    if(b.dataset.resume){closeModal();setup=false;flipped=false;return command('resume',{game_id:b.dataset.resume});}
    switch(b.dataset.action){
      case 'visual-prev':
      case 'visual-next':visualIndex=Math.max(0,Math.min(state.game.coach.visuals.length-1,visualIndex+(b.dataset.action==='visual-next'?1:-1)));visualHidden=false;renderBoard();renderCoach();break;
      case 'moves':showMoves();break;
      case 'coach-info':modal('<h2 id="modal-title">Dein Coach</h2><p>Lokales Modell: '+esc(state.coach_model||'Ollama')+'. Es antwortet auf Deutsch oder Englisch. KI-Antworten können Fehler enthalten. Markierungen und Pfeile beruhen auf geprüften Brettdaten.</p><p>Mit „Mehr Hilfe“ erhältst du weitere Hinweise. Du kannst jederzeit weiterspielen. Eine leere Nachricht fordert einen neuen Impuls an.</p>');break;
      case 'toggle-visual':visualHidden=!visualHidden;renderBoard();renderCoach();break;
      case 'close-modal':closeModal();break;
      case 'setup-next':step=Math.min(2,step+1);render();break;
      case 'setup-back':step=Math.max(0,step-1);render();break;
      case 'setup-cancel':setup=false;render();break;
      case 'new-menu':newMenu();break;
      case 'new-setup':closeModal();setup=true;step=2;draft={...state.profile};render();break;
      case 'onboard-again':closeModal();setup=true;step=0;draft={...state.profile};render();break;
      case 'start':if(await command('settings',{settings:draft})){if(await command('new')){setup=false;flipped=false;render();}}break;
      case 'example':closeModal();setup=false;flipped=false;await command('example');break;
      case 'draw':drawMode=!drawMode;arrowStart=null;selected=null;renderBoard();break;
      case 'clear-arrows':arrows=[];arrowStart=null;drag=null;renderAnnotations();$('#drawing-status').textContent='Eigene Pfeile gelöscht.';break;
      case 'toggle-advantage':await command('settings',{settings:{show_advantage:state.profile.show_advantage===false}});break;
      case 'preview-sound':sounds.unlock();setTimeout(()=>{sounds.play(false);sounds.play(true,.3);},40);break;
      case 'flip':flipped=!flipped;selected=null;render();break;
      case 'history':await history();break;
      case 'settings':settings();break;
      case 'note':await command('note',{note:$('#reflection').value});break;
      case 'resign-menu':modal('<h2 id="modal-title">Partie beenden?</h2><p>Die Partie wird als aufgegeben gespeichert.</p>'+button('resign','Partie aufgeben',true));break;
      case 'resign':closeModal();await command('resign');break;
      default:if(b.dataset.action){selected=null;await command(b.dataset.action);}
    }
  });
  root.addEventListener('submit',async e=>{
    if(e.target.id==='coach-chat-form'){
      e.preventDefault();const text=coachDraft.trim()||(state.game.coach.stage===2?'Please explain the revealed idea briefly.':'Please ask me one short guiding question about this hint without revealing the answer.');
      if(await command('coach_chat',{text})){coachDraft='';renderCoach();}
      return;
    }
    if(e.target.id!=='settings-form')return;e.preventDefault();const f=new FormData(e.target);
    if(await command('settings',{settings:{name:f.get('name'),level:f.get('level'),auto_coach:f.has('auto_coach'),show_advantage:f.has('show_advantage'),sound:f.has('sound')}}))closeModal();
  });
  root.addEventListener('input',e=>{if(e.target.id==='coach-question')coachDraft=e.target.value;if(e.target.id==='reflection')noteDraft=e.target.value;});
  root.addEventListener('change',e=>{if(e.target.id==='visual-scene'){visualIndex=Number(e.target.value);visualHidden=false;renderBoard();renderCoach();$('#visual-scene').focus();}});
  root.addEventListener('keydown',e=>{if(e.target.id==='coach-question'&&e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();if(!busy&&!state.game.coach?.llm_pending)e.target.form.requestSubmit();}});
  $('#board').addEventListener('keydown',e=>{
    const sq=e.target.dataset.square;if(!sq)return;
    if(e.key==='Escape'){arrows=[];arrowStart=null;drag=null;drawMode=false;selected=null;renderBoard();paintIcons();$(`[data-square="${sq}"]`).focus();return;}
    const {files,ranks}=order(),index=ranks.indexOf(Number(sq[1]))*8+files.indexOf(sq[0]);
    const next={ArrowRight:index+1,ArrowLeft:index-1,ArrowDown:index+8,ArrowUp:index-8}[e.key];
    if(next!==undefined){e.preventDefault();const i=Math.max(0,Math.min(63,next));$(`[data-square="${files[i%8]+ranks[Math.floor(i/8)]}"]`).focus();}
  });
  root.addEventListener('pointerdown',()=>{if(state?.profile.sound!==false)sounds.unlock();},{capture:true});
  root.addEventListener('keydown',()=>{if(state?.profile.sound!==false)sounds.unlock();},{capture:true});
  const boardElement=$('#board');
  const squareAt=e=>document.elementFromPoint(e.clientX,e.clientY)?.closest('#board [data-square]')?.dataset.square;
  boardElement.addEventListener('contextmenu',e=>e.preventDefault());
  boardElement.addEventListener('pointerdown',e=>{
    if(e.button!==2&&!(drawMode&&e.button===0))return;
    const from=squareAt(e);if(!from)return;
    if(e.button===2)e.preventDefault();
    drag={from,to:from,id:e.pointerId,right:e.button===2};
    boardElement.setPointerCapture(e.pointerId);
  });
  boardElement.addEventListener('pointermove',e=>{
    if(!drag||drag.id!==e.pointerId)return;
    drag.to=squareAt(e);renderAnnotations();
  });
  boardElement.addEventListener('pointerup',e=>{
    if(!drag||drag.id!==e.pointerId)return;
    const {from,right}=drag,to=squareAt(e);drag=null;
    if(boardElement.hasPointerCapture(e.pointerId))boardElement.releasePointerCapture(e.pointerId);
    if(to&&from!==to)toggleArrow(from,to);
    else if(to&&!right){if(arrowStart){toggleArrow(arrowStart,to);arrowStart=null;}else arrowStart=to;}
    if(!right){suppressClick=true;setTimeout(()=>suppressClick=false,0);}
    renderAnnotations();
  });
  boardElement.addEventListener('pointercancel',()=>{drag=null;renderAnnotations();});
  window.addEventListener('blur',()=>{drag=null;renderAnnotations();});
  paintIcons();refresh();setInterval(refresh,700);
})();
