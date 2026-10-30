import os
import re
import time
from .languages import COPY, detect
from .retrieval import RuleIndex, normalize
from .state import Store
from .model import enabled

# Matching determines triage, never guilt. Phrases are deliberately auditable.
SIGNALS = {
 'account': r'взлом|украл.*акк|украли.*акк|потерял.*доступ|не могу (?:зайти|войти)|аккаунт.*(?:пропал|украден)|hacked|lost access|аккаунтым|akkauntim|hisobim|cuenta.*rob|conta.*roub',
 'payment': r'донат|плат[её]ж|оплат|деньги.*не приш|гк.*не приш|payment|paid|to‘lov|to\x27lov|tolov|төлем|pago|pagamento',
 'appeal': r'разбан|обжал|апелляц|бан.*(?:причин|сним|ошиб)|мут.*(?:причин|сним|ошиб)|(?:забанили|забанен|выдали бан)|unban|appeal|banned|банды|banim|ban.*olib',
 'admin': r'админ.*(?:выдал|наказ|наруш|оскорб|бездейств)|жалоб.*админ|admin.*(?:abuse|insult)',
 'cheat': r'\bчит|\bсофт|\bsoft\b|aimbot|аим|летает|сквозь стен|через стен|cheat|wallhack|speedhack',
 'scam': r'обман|мошенн|скам|scam|алда|aldadi|отдал.*(?:не вер|не отдал)|взял.*не отдал',
 'rmt_ads': r'реклам|за реал|прода[ею].*акк|rmt|advertis|sell.*account|real money',
 'insult': r'оск|родн|матер|\bмать\b|расизм|токсич|insult|haqorat|балағат|қорла|ofens|xinga',
 'dm': r'\bdm\b|\bдм\b|\bдб\b|убил|убива|стреля|убий|kill|otdi|o‘ldir|өлтір|атқан|matar',
 'help': r'застр|текстур|баг|телепорт|упал.*карт|stuck|bug|qotib|тұрып қал|қатып|atascado|preso',
 'question': r'как |где |зачем |сколько |почему |how |where |qanday|qayer|қалай|қайда|como |cómo ',
 'threat': r'докс|угрож.*(?:жизн|реал|убить)|адрес.*(?:найд|приед)|death threat|doxx',
 'mass': r'массов.*баг|весь сервер.*(?:лежит|вылет)|всех.*(?:кикает|вылет)|server.*(?:down|crash)',
}
SIGNALS['account'] += r'|пропал[аи]?.*(?:машин|имуществ|автомобил)|украли.*(?:машин|имуществ)|missing (?:car|property)|көлігім.*жоғал|mashinam.*yo.q'
SIGNALS['compromise'] = r'взлом|украл.*акк|украли.*акк|потерял.*доступ|не могу (?:зайти|войти)|аккаунт.*(?:пропал|украден)|hacked|lost access|аккаунтым.*(?:бұз|ұрла)|akkauntim.*(?:buz|o.g.ir)|cuenta.*rob|conta.*roub'
SIGNALS['help'] += r'|помогите выбраться|шыға алмай|chiqa olmay|qued[eé].*atrap|fiquei.*preso'
SIGNALS['dm'] += r'|дмят|сбил|таран|\bdb\b|өлтір|o.ldir|matou|matado'
SIGNALS['scam'] += r'|вымога|не отдал.*(?:машин|деньг)|алдан|aldan|estaf|enganou'
SIGNALS['question'] += r'|подскажите|лицензи|устроиться|қайдан|qayerdan|como faço|d[oó]nde'
SIGNALS['payment'] += r'|төл[её]|ақша.*түсп|pul.*kelma|paguei|pagu[eé]'

REFS = {
 'complaint.insult': ['2.1','2.4','2.6'], 'complaint.cheat':['5.2'],
 'complaint.dm':['5.3','5.4'], 'complaint.scam':['4.1','4.2'],
 'complaint.rmt_ads':['2.3','4.4'], 'complaint.admin':['3.4'],
 'report.account':['1.4'],
}

def input_view(ticket):
    """Strict allowlist: outcomes/admin replies cannot enter inference or RAG."""
    if not isinstance(ticket,dict):raise ValueError('ticket must be a JSON object')
    kind = ticket.get('kind', 'report')
    if kind not in ('report','complaint'):
        raise ValueError('kind must be complaint or report')
    messages = ticket.get('messages', [])
    if not isinstance(messages, list) or len(messages) > 100:
        raise ValueError('messages must be a list with at most 100 items')
    clean = []
    for m in messages:
        if not isinstance(m, dict):
            raise ValueError('each message must be an object')
        if m.get('role') in ('player','reported_player'):
            t = m.get('text', '')
            if not isinstance(t,str) or len(t) > 20000:
                raise ValueError('text must be a string with at most 20000 characters')
            a = m.get('attachments',0)
            clean.append({'role':m['role'],'text':t,'attachments':a if isinstance(a,int) and not isinstance(a,bool) and a>0 else 0})
    return {'kind':kind, 'messages':clean, **{k:ticket.get(k) for k in
        ('ticket_id','created_at','reporter_hash','reported_hash','reported_nick','rule_refs_raw','images_count','server','region','server_lang')}}

class Engine:
    def __init__(self, rules_path, store=None):
        self.index = RuleIndex(rules_path)
        self.store = store or Store()

    def triage(self, ticket):
        started = time.perf_counter()
        v = input_view(ticket)
        player = '\n'.join(m['text'] for m in v['messages'] if m['role']=='player')
        opposing = '\n'.join(m['text'] for m in v['messages'] if m['role']=='reported_player')
        t = normalize(player)
        flags = {k:bool(re.search(p,t)) for k,p in SIGNALS.items()}
        language = detect(player)
        reply_language = language if language in COPY else 'ru'
        kind = v['kind']
        if kind == 'complaint':
            label = next((k for k in ['admin','cheat','scam','rmt_ads','insult','dm'] if flags[k]), None)
            category = 'complaint.'+(label or ('invalid' if len(t.strip())<8 or flags['question'] or flags['help'] else 'other'))
        else:
            label = next((k for k in ['account','payment','help'] if flags[k]),None)
            category = 'report.'+(label or ('complaint' if any(flags[k] for k in ['cheat','insult','dm','scam','rmt_ads']) else 'question' if flags['question'] else 'offtopic'))
        if flags['appeal'] or flags['admin']:
            category = 'complaint.admin' if kind=='complaint' else category
        classifier_status='disabled'
        semantic_uncertain=False
        semantic=None
        if enabled():
            from .model import classify
            candidates=self.index.search(player,REFS.get(category,[]),limit=4)
            grounded=[r for r in self.index.points if r['section_id']==30 and r['ref'] in REFS.get(category,[])][:2]
            if category=='complaint.dm':grounded=[r for r in self.index.points if r['section_id']==31 and r['ref']=='1.1.1']
            candidates=(grounded+[r for r in candidates if r['id'] not in {g['id'] for g in grounded}])[:3]
            semantic,classifier_status=classify(v,candidates)
            if semantic:
                category=semantic['category'];language=semantic['lang']
                reply_language=language if language in COPY else 'ru'
                for k,source in [('account','account_compromise'),('payment','payment'),('appeal','appeal'),('threat','real_world_threat'),('mass','mass_bug')]:
                    flags[k]=flags[k] or semantic[source]
                flags['compromise']=flags['compromise'] or semantic['account_compromise']
                semantic_uncertain=semantic['uncertain']
        # Mandatory routing also follows the semantic category, even if a model flag disagrees.
        flags['payment']=flags['payment'] or category=='report.payment'
        flags['account']=flags['account'] or category=='report.account'
        flags['cheat']=flags['cheat'] or category=='complaint.cheat'
        flags['rmt_ads']=flags['rmt_ads'] or category=='complaint.rmt_ads'
        attachments = sum(m['attachments'] for m in v['messages'] if m['role']=='player')
        raw_count = v.get('images_count')
        if isinstance(raw_count,int) and not isinstance(raw_count,bool):
            attachments = max(attachments,raw_count)
        evidence = attachments > 0 or bool(re.search(r'https?://|<url>',player))
        priority = 'p2'
        if category in ('report.question','report.offtopic','complaint.invalid'):
            priority='p3'
        if category.startswith('complaint.') and not evidence:
            priority='p3'
        if flags['cheat'] or flags['rmt_ads'] or (flags['scam'] and re.search(r'миллион|\bмлн\b|million',t)) or (kind=='complaint' and evidence):
            priority='p1'
        if flags['compromise'] or flags['payment'] or flags['threat'] or flags['mass']:
            priority='p0'
        nickname = v.get('reported_nick')
        if not isinstance(nickname,str) or not nickname:
            match = re.search(r'\b[A-Za-z][A-Za-z0-9]*_[A-Za-z][A-Za-z0-9_]*\b',player)
            nickname = match.group() if match else None
        server_match=re.search(r'(?:сервер(?:е|а)?|server)\s*[№#:]?\s*(\d{1,3})\b',t)
        server=v.get('server') or (server_match.group(1) if server_match else None)
        scope = '|'.join(str(v.get(k) or '') for k in ['reporter_hash','kind','region','server','reported_hash']) if v.get('reporter_hash') else None
        duplicate = self.store.duplicate(scope,t,v.get('created_at'),v.get('ticket_id'))
        empty = len(re.findall(r'\w+',t))<2 and not any(flags.values())
        # Only category-grounded general rules are eligible for citation.
        # A player-provided reference is preserved as an allegation, not treated as authoritative.
        refs = REFS.get(category,[])
        if category=='report.complaint':
            refs = REFS.get('complaint.'+next((k for k in ['cheat','scam','rmt_ads','insult','dm'] if flags[k]),'other'),[])
        if flags['threat']:
            refs = ['2.6']
        retrieved = self.index.search(player,refs,limit=8)
        eligible = [dict(r,score=next((c['score'] for c in retrieved if c['id']==r['id']),0))
                    for r in self.index.points if r['section_id']==30 and r['ref'] in refs]
        eligible.sort(key=lambda r:refs.index(r['ref']))
        # Choose the precise topical rule, rather than all taxonomy candidates.
        preferred = None
        if category=='complaint.insult':
            preferred='2.4' if 'расизм' in t else '2.6' if flags['threat'] else '2.1'
        if preferred:
            eligible.sort(key=lambda r:r['ref']!=preferred)
        # The draft taxonomy maps generic DM to 5.3/5.4, but those points address
        # leaving RP / house territory. Ground the citation in the actual source.
        if category in ('complaint.dm','report.complaint') and flags['dm']:
            if re.search(r'зелен|зелён|\bgz\b|green zone|жасыл',t):
                eligible=[dict(r,score=0) for r in self.index.points if r['section_id']==32 and r['ref']=='1.1']
            elif re.search(r'у дома|в доме|территори.*дома|квартир',t):
                eligible=[dict(r,score=0) for r in self.index.points if r['section_id']==30 and r['ref']=='5.4']
            else:
                # Cite the real complaint-evidence requirement, not a fabricated
                # numbered DM rule. The unnumbered glossary remains retrieval context.
                eligible=[dict(r,score=0,citation_purpose='complaint_review') for r in self.index.points if r['section_id']==31 and r['ref']=='1.1.1']
        if kind=='complaint' and not eligible:
            procedural_ref='1.1.2' if category=='complaint.invalid' and flags['question'] else '1.3.1'
            eligible=[dict(r,score=0,citation_purpose='complaint_review') for r in self.index.points if r['section_id']==31 and r['ref']==procedural_ref]
        cited = eligible[:1]
        human = kind=='complaint' or category not in ('report.offtopic',) or flags['account'] or flags['payment'] or flags['appeal']
        reasons=[]
        if kind=='complaint' or category=='report.complaint': reasons.append('Утверждения игрока требуют проверки; решение о нарушении принимает администратор')
        if evidence: reasons.append('Есть метаданные вложений; содержимое не просмотрено')
        if flags['account'] or flags['payment'] or flags['appeal'] or category=='complaint.admin':
            human=True; reasons.append('Обязательная эскалация: аккаунт, платёж, апелляция или жалоба на администратора')
        if language=='und':
            human=True; reasons.append('Язык не определён уверенно; черновик на русском требует проверки')
        if semantic_uncertain:
            human=True; reasons.append('Семантическая модель отметила неоднозначность запроса')
        if opposing: reasons.append('Комментарий обвиняемого сохранён отдельно от утверждений заявителя')
        if refs and not cited:
            human=True; reasons.append('Не найден проверенный релевантный пункт правил')
        if category in ('report.question','report.help'):
            reasons.append('Нет проверенной базы игровых инструкций; конкретные действия не выдумываются')
        if duplicate: reasons.append('Точное совпадение нормализованного текста от того же заявителя в пределах часа')
        copy=COPY[reply_language]
        parts=[copy['hello']]
        if duplicate: parts.append(copy['duplicate'])
        if flags['payment']: parts.append(copy['payment'])
        elif flags['account']: parts.append(copy['account'])
        elif flags['appeal']: parts.append(copy['appeal'])
        elif category in ('report.offtopic','complaint.invalid'): parts.append(copy['empty'])
        elif category=='report.question': parts.append(copy['question'])
        elif category=='report.help': parts.append(copy['help'])
        else:
            parts.append(copy['claim'])
            # Ask for missing facts only; do not request an already supplied nickname or files.
            names={
              'ru':('Уточните: ',['ник игрока','сервер','время события','доказательства, если они есть']),
              'kk':('Нақтылаңыз: ',['ойыншының аты','сервер','оқиға уақыты','бар болса, дәлелдер']),
              'uz':('Aniqlashtiring: ',['o‘yinchi nomi','server','voqea vaqti','mavjud bo‘lsa, dalillar']),
              'en':('Please provide: ',['player name','server','incident time','any available evidence']),
              'es':('Indica: ',['nombre del jugador','servidor','hora del incidente','pruebas disponibles']),
              'pt':('Informe: ',['nome do jogador','servidor','horário do incidente','provas disponíveis'])}
            prefix,fields=names[reply_language]
            missing=[field for field,known in zip(fields,[bool(nickname),bool(server),False,evidence]) if not known]
            parts.append(prefix+', '.join(missing)+'.')
        if evidence: parts.append(copy['evidence'])
        for r in cited:
            if r.get('citation_type')=='section':
                section_copy={
                    'ru':'Основание для проверки: раздел «{ref}». Описание термина не подтверждает нарушение.',
                    'kk':'Тексеру негізі: «{ref}» бөлімі. Терминнің сипаттамасы бұзушылықты растамайды.',
                    'uz':'Tekshirish uchun manba: «{ref}» bo‘limi. Atama tavsifi qoidabuzarlikni tasdiqlamaydi.',
                    'en':'Review source: the “{ref}” section. A definition does not establish a violation.',
                    'es':'Fuente para la revisión: sección «{ref}». La definición no confirma una infracción.',
                    'pt':'Fonte para análise: seção «{ref}». A definição não confirma uma infração.'}
                parts.append(section_copy[reply_language].format(ref=r['ref']))
            else: parts.append(copy['rule'].format(ref=r['ref'],section=r['section']))
        if human: parts.append(copy['human'])
        claimed_refs=re.findall(r'(?<!\d)\d{1,2}\.\d+(?:\.\d+)?', str(v.get('rule_refs_raw') or '')+' '+player)
        # This score is a heuristic, not a calibrated probability.
        score=.78 if any(flags.values()) else .35
        if language=='und': score=min(score,.35)
        result={
            'lang':language,'category':category,'priority':priority,
            'is_spam_or_duplicate':bool(duplicate or empty),
            'extracted':{'nickname':nickname,'rule_refs':list(dict.fromkeys(claimed_refs)),
                'has_evidence':evidence,'server':server},
            'draft_reply':{'lang':reply_language,'text':' '.join(parts),'cited':[r['ref'] for r in cited]},
            'needs_human':bool(human),'confidence':score,'reasons':reasons,
            'audit':{'mode':'semantic_rag_templates' if classifier_status=='accepted' else 'retrieval_templates',
                'classifier_status':classifier_status,'confidence_type':'uncalibrated_heuristic',
                'rule_sources':cited,'retrieved_candidates':retrieved[:4],
                'claims':[{'role':m['role'],'text':m['text'],'verified':False} for m in v['messages']],
                'attachments':{'count':attachments,'inspected':False},
                'generation_cost_usd':semantic['_billing']['estimated_cost_usd'] if semantic else (None if enabled() else 0),
                'model_billing':semantic.get('_billing') if semantic else None,
                'cost_note':'API cost estimate from usage; failed-call billing unknown. Hardware and labour excluded' if enabled() else 'No paid API calls; hardware and labour excluded',
                'latency_ms':0,'duplicate':duplicate,'spam':empty},
        }
        if semantic:
            from .model import validate_wording
            proposed=semantic.get('draft_text','')
            source_ids={s['id'] for s in cited}
            draft_language=detect(proposed)
            language_matches=draft_language in (reply_language,'und')
            if set(semantic.get('cited_ids',[]))==source_ids and language_matches and validate_wording(proposed,result):
                result['draft_reply']['text']=proposed
                result['needs_human']=True
                result['audit']['mode']='llm_rag'
                result['audit']['draft_status']='accepted_for_human_review'
                result['reasons'].append('Черновик LLM требует смысловой проверки администратором')
            else:
                result['audit']['draft_status']='rejected_used_safe_template'
        result['audit']['latency_ms']=round((time.perf_counter()-started)*1000,3)
        return result
