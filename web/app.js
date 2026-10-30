'use strict';
const $=id=>document.getElementById(id);
const uid=()=>window.crypto?.randomUUID?crypto.randomUUID():Date.now().toString(36)+Math.random().toString(36).slice(2);
const tickets=[
 {title:'Платёж не зачислен',kind:'report',priority:'p0',text:'Оплатил донат, деньги списались, но ГК не пришли. Что делать?',attachments:0},
 {title:'Жалоба на оскорбления',kind:'complaint',priority:'p1',text:'Demo_Player оскорблял меня и мою семью в чате. Приложил скриншоты, пункт 2.1.',attachments:2},
 {title:'Қазақша өтініш',kind:'report',priority:'p0',text:'Сәлеметсіз бе! Аккаунтым бұзылды, ойынға кіре алмаймын. Көмек беріңіз.',attachments:0},
 {title:'O‘zbekcha murojaat',kind:'report',priority:'p0',text:'Salom! To‘lov qildim, lekin pulim kelmadi. Iltimos yordam bering.',attachments:0},
 {title:'Игрок застрял',kind:'report',priority:'p2',text:'Застрял в текстурах возле больницы, не могу выйти.',attachments:0},
 {title:'Апелляция наказания',kind:'complaint',priority:'p3',text:'Меня забанили без причины. Снимите бан, пожалуйста.',attachments:0},
 {title:'Пустой репорт',kind:'report',priority:'p3',text:'ау',attachments:0},
];
tickets.forEach(t=>{t.id='demo-'+uid();});
let active=-1,result=null,requestVersion=0;
function renderQueue(){
 $('queue').replaceChildren();
 tickets.forEach((t,i)=>{if($('filter').value!=='all'&&t.priority!==$('filter').value)return;
  const b=document.createElement('button');b.className='ticket'+(i===active?' active':'');
  const p=document.createElement('span');p.className='pill '+t.priority;p.textContent=t.priority.toUpperCase();
  const title=document.createElement('strong');title.textContent=t.title;
  const sub=document.createElement('small');sub.textContent=(t.kind==='complaint'?'Жалоба':'Репорт')+' · '+t.attachments+' вложений';
  b.append(p,title,sub);b.onclick=()=>selectTicket(i);$('queue').append(b);
 });
}
async function api(path,body){
 if(window.GRAND_DESKTOP){const method={'/triage':'triage','/feedback':'feedback'}[path];if(!method)throw Error('Unknown method');const data=await window.pywebview.api[method](body);if(data.error)throw Error(data.error);return data;}
 const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error||'Ошибка сервиса');return data;
}
async function selectTicket(i){
 const version=++requestVersion;active=i;result=null;renderQueue();$('empty').classList.add('hidden');$('workspace').classList.remove('hidden');
 const t=tickets[i];$('title').textContent=t.title;$('message').textContent=t.text;$('reply').value='Обработка…';$('status').textContent='';
 ['approve','save','escalate','json'].forEach(k=>$(k).disabled=true);
 try{
 const response=await api('/triage',{ticket_id:t.id,kind:t.kind,messages:[{role:'player',text:t.text,attachments:t.attachments}]});
 if(version!==requestVersion)return;result=response;t.priority=result.priority;renderQueue();
 $('reply').value=result.draft_reply.text;$('lang').textContent=result.lang.toUpperCase();
 $('meta').textContent='Канал: '+t.kind+' · Вложения: '+t.attachments+' · Содержимое вложений не проверено';
 $('subtitle').textContent=result.category+' / '+result.priority.toUpperCase();
 $('warning').textContent=result.needs_human?'Требуется администратор. Черновик не является решением по жалобе.':'Можно использовать как уточняющий ответ. Решение по существу не принималось.';
 if(result.audit.classifier_status.startsWith('fallback')||result.audit.classifier_status.startsWith('rejected'))$('warning').textContent+=' AI-запрос не выполнен или ответ не прошёл проверку: использован локальный режим.';
 else if(result.audit.draft_status==='rejected_used_safe_template')$('warning').textContent+=' Формулировка AI заменена проверенным шаблоном.';
 $('mode').textContent=result.audit.mode.includes('llm')?'LLM + RAG':result.audit.mode==='semantic_rag_templates'?'SEMANTIC + TEMPLATES':'RETRIEVAL + TEMPLATES';
 $('facts').replaceChildren();
 [['Приоритет',result.priority.toUpperCase()],['Категория',result.category],['Язык',result.lang],['Вложения',result.extracted.has_evidence?'Есть, не просмотрены':'Нет'],['Дубликат',result.audit.duplicate?'Да':'Нет'],['Confidence',result.confidence.toFixed(2)]].forEach(([k,v])=>{const s=document.createElement('span');s.textContent=k;const b=document.createElement('b');b.textContent=v;$('facts').append(s,b);});
 $('reasons').replaceChildren();for(const reason of result.reasons){const li=document.createElement('li');li.textContent=reason;$('reasons').append(li);}
 if(!result.reasons.length){const li=document.createElement('li');li.textContent='Уточняющий ответ без решения по существу.';$('reasons').append(li);}
 $('sources').replaceChildren();for(const source of result.audit.rule_sources){const box=document.createElement('div');box.className='rule';const ref=document.createElement('b');ref.className='source';ref.textContent='§ '+source.ref+' · '+source.section;const p=document.createElement('p');p.textContent=source.text;box.append(ref,p);$('sources').append(box);}
 if(!result.audit.rule_sources.length){const p=document.createElement('p');p.className='small muted';p.textContent='Пункт не цитируется: нет подходящего основания для этого черновика.';$('sources').append(p);}
 $('timing').textContent=result.audit.latency_ms+' мс · '+(result.audit.generation_cost_usd===null?'Стоимость API неизвестна':result.audit.generation_cost_usd===0?'Без платных API-вызовов':'API ≈ $'+result.audit.generation_cost_usd.toFixed(6));
 ['approve','save','escalate','json'].forEach(k=>$(k).disabled=false);
 }catch(e){if(version!==requestVersion)return;$('reply').value='';$('status').textContent=e.message;}
}
async function feedback(action){if(!result)return;try{await api('/feedback',{ticket_id:tickets[active].id,action,original_text:result.draft_reply.text,edited_text:$('reply').value,category:result.category,lang:result.lang,needs_human:result.needs_human});$('status').textContent=action==='escalate'?'Эскалация сохранена локально.':'Обратная связь сохранена. Игроку ничего не отправлено.';}catch(e){$('status').textContent=e.message;}}
$('new').onclick=()=>$('composer').showModal();$('cancel').onclick=()=>$('composer').close();$('filter').onchange=renderQueue;
$('process').onclick=()=>{const text=$('text').value.trim();if(!text){$('text').focus();return;}tickets.unshift({id:'custom-'+uid(),title:text.slice(0,45),kind:$('kind').value,priority:'p2',text,attachments:Math.max(0,Math.min(100,Number($('attachments').value)||0))});$('composer').close();$('text').value='';$('filter').value='all';if(window.GRAND_DESKTOP)window.pywebview.api.save_queue(tickets.filter(t=>t.id.startsWith('custom-')));selectTicket(0);};
$('approve').onclick=()=>feedback('approve_draft');$('save').onclick=()=>feedback('edit');$('escalate').onclick=()=>feedback('escalate');
$('json').onclick=()=>{if(result){$('raw').textContent=JSON.stringify(result,null,2);$('jsondialog').showModal();}};$('closejson').onclick=()=>$('jsondialog').close();
async function refreshHealth(){const h=window.GRAND_DESKTOP?await window.pywebview.api.health():await (await fetch('/health')).json();$('health').textContent='● '+(h.provider||'offline').toUpperCase()+' / '+h.rule_points+' источников';return h;}
async function boot(){
 try{const h=await refreshHealth();if(window.GRAND_DESKTOP){$('settings').classList.remove('hidden');const saved=await window.pywebview.api.load_queue();if(Array.isArray(saved))tickets.unshift(...saved.filter(t=>t&&typeof t.text==='string'&&typeof t.id==='string'));if(h.status==='needs_rules')$('settingsdialog').showModal();}renderQueue();if(h.status!=='needs_rules')selectTicket(0);}catch(e){$('health').textContent='Сервис недоступен';}
}
$('settings').onclick=()=>$('settingsdialog').showModal();$('closesettings').onclick=()=>$('settingsdialog').close();
$('connectgroq').onclick=async()=>{try{const value=$('apikey').value;const r=await window.pywebview.api.configure_groq(value,'openai/gpt-oss-120b');$('apikey').value='';$('settingsstatus').textContent=r.error||'Groq настроен. Ключ сохранён только в памяти. Доступность API проверится при обработке обращения.';await refreshHealth();}catch(e){$('settingsstatus').textContent='Не удалось подключить Groq.';}};
$('disconnectgroq').onclick=async()=>{await window.pywebview.api.disconnect_groq();$('apikey').value='';$('settingsstatus').textContent='Включён локальный режим.';await refreshHealth();};
$('importrules').onclick=async()=>{const r=await window.pywebview.api.import_rules();$('settingsstatus').textContent=r.error||(r.loaded?'Правила загружены: '+r.rule_points+' источников.':'Выбор отменён.');await refreshHealth();if(r.loaded){$('settingsdialog').close();selectTicket(Math.max(0,active));}};
if(window.GRAND_DESKTOP)window.addEventListener('pywebviewready',boot);else boot();
