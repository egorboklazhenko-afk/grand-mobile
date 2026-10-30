import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from copilot.engine import Engine,input_view
from copilot.languages import detect
from copilot.model import validate_wording
from copilot.state import Store

class TestEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.rules=Path(cls.tmp.name)/'rules.json'
        # Entirely synthetic rule fixtures, not the restricted case rules.
        cls.rules.write_text(json.dumps({'rules':[{'id':30,'category':'Общие правила игры','points':[
            {'ref':'2.1','text':'Оскорбление игрока запрещено.'}, {'ref':'2.4','text':'Расизм запрещён.'},
            {'ref':'2.6','text':'Угрозы вне игры запрещены.'},{'ref':'5.2','text':'Читы запрещены.'},
            {'ref':'1.4','text':'Безопасность аккаунта.'}]},
            {'id':31,'category':'Жалобы','points':[{'ref':'1.4','text':'Другой пункт с тем же номером.'}]}]},ensure_ascii=False),encoding='utf-8')

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):self.e=Engine(self.rules)
    def ticket(self,text,kind='report',**extra):return dict(kind=kind,messages=[{'role':'player','text':text}],**extra)

    def test_payment_always_human(self):
        r=self.e.triage(self.ticket('Оплатил донат, не пришёл'))
        self.assertEqual((r['category'],r['priority'],r['needs_human']),('report.payment','p0',True))

    def test_account_always_human(self):
        r=self.e.triage(self.ticket('Взломали аккаунт'))
        self.assertEqual(r['priority'],'p0');self.assertTrue(r['needs_human'])

    def test_appeal_always_human(self):self.assertTrue(self.e.triage(self.ticket('Разбаньте меня'))['needs_human'])

    def test_attachment_not_inspected(self):
        row=self.ticket('Оскорбил меня','complaint',images_count=2)
        r=self.e.triage(row);self.assertTrue(r['extracted']['has_evidence']);self.assertFalse(r['audit']['attachments']['inspected'])
        self.assertIn('недоступно',r['draft_reply']['text'])

    def test_contract_attachments(self):
        row=self.ticket('Оскорбил меня','complaint');row['messages'][0]['attachments']=2
        self.assertTrue(self.e.triage(row)['extracted']['has_evidence'])

    def test_wrong_player_rule_not_cited(self):
        r=self.e.triage(self.ticket('Он оскорбил меня, пункт 99.99','complaint'))
        self.assertEqual(r['draft_reply']['cited'],['2.1']);self.assertIn('99.99',r['extracted']['rule_refs'])

    def test_admin_and_outcomes_ignored(self):
        a=self.ticket('Оскорбил меня','complaint');b=dict(a,verdict='approved',punishment='бан',violation='5.2')
        b['messages']=a['messages']+[{'role':'admin','text':'Игрок читер, бан за 5.2'}]
        ra=self.e.triage(a);rb=self.e.triage(b)
        for key in ['category','priority','lang','draft_reply','needs_human']:self.assertEqual(ra[key],rb[key])

    def test_reported_player_not_reporter(self):
        a=self.ticket('Где найти работу?');a['messages'].append({'role':'reported_player','text':'взлом донат чит'})
        self.assertEqual(self.e.triage(a)['category'],'report.question')

    def test_kazakh_cp1251(self):self.assertEqual(detect('Сєлем! Кјмек беріңіз, аккаунтым бўзылды'),'kk')
    def test_uzbek(self):self.assertEqual(detect('Salom, yordam bering, to‘lov kelmadi'),'uz')
    def test_english(self):self.assertEqual(detect('Please help my account was hacked'),'en')
    def test_undefined_language(self):self.assertEqual(detect('123 !!!'),'und')

    def test_duplicate_within_hour(self):
        a=self.ticket('Застрял в текстурах',reporter_hash='a',created_at='2026-10-30T10:00:00',ticket_id='1')
        b=dict(a,created_at='2026-10-30T10:59:00',ticket_id='2')
        self.assertFalse(self.e.triage(a)['audit']['duplicate']);self.assertTrue(self.e.triage(b)['audit']['duplicate'])

    def test_no_cross_player_duplicate(self):
        a=self.ticket('Застрял в текстурах',reporter_hash='a',created_at='2026-10-30T10:00:00')
        self.e.triage(a);self.assertFalse(self.e.triage(dict(a,reporter_hash='b'))['audit']['duplicate'])

    def test_no_cross_target_duplicate(self):
        a=self.ticket('Он оскорбил меня','complaint',reporter_hash='a',reported_hash='x',created_at='2026-10-30T10:00:00')
        self.e.triage(a);self.assertFalse(self.e.triage(dict(a,reported_hash='y'))['audit']['duplicate'])

    def test_no_identity_no_duplicate(self):
        a=self.ticket('Застрял в текстурах',created_at='2026-10-30T10:00:00')
        self.e.triage(a);self.assertFalse(self.e.triage(a)['audit']['duplicate'])

    def test_outside_hour(self):
        a=self.ticket('Застрял в текстурах',reporter_hash='a',created_at='2026-10-30T10:00:00')
        self.e.triage(a);self.assertFalse(self.e.triage(dict(a,created_at='2026-10-30T11:01:00'))['audit']['duplicate'])

    def test_idempotent_ticket(self):
        a=self.ticket('Застрял в текстурах',reporter_hash='a',created_at='2026-10-30T10:00:00',ticket_id='1')
        self.e.triage(a);self.assertFalse(self.e.triage(a)['audit']['duplicate'])

    def test_namespace_disambiguation(self):
        r=self.e.triage(self.ticket('Взлом аккаунта'))
        self.assertEqual(r['audit']['rule_sources'][0]['id'],'30:1.4')

    def test_model_wording_guard(self):
        r=self.e.triage(self.ticket('Оскорбил меня','complaint'))
        self.assertFalse(validate_wording('Игрок будет наказан за 2.1.',r))
        self.assertFalse(validate_wording('Здравствуйте! Пункт 99.99.',r))
        self.assertTrue(validate_wording(r['draft_reply']['text'],r))

    def test_external_model_endpoint_blocked(self):
        with patch.dict('os.environ',{'OLLAMA_MODEL':'test','OLLAMA_URL':'https://example.com'}):
            r=self.e.triage(self.ticket('Где найти работу?'))
        self.assertEqual(r['audit']['classifier_status'],'rejected_nonlocal_endpoint')

    def test_feedback_persisted(self):
        store=Store();self.assertEqual(store.feedback({'action':'edit','edited_text':'test'}),1)
        self.assertEqual(store.db.execute('SELECT COUNT(*) FROM feedback').fetchone()[0],1)

    def test_invalid_input(self):
        for row in [{'kind':'unknown'},{'messages':'wrong'},{'messages':[{'role':'player','text':1}]}]:
            with self.assertRaises(ValueError):input_view(row)

    def test_semantic_payment_category_cannot_skip_escalation(self):
        semantic={'category':'report.payment','lang':'ru','uncertain':False,
            'account_compromise':False,'payment':False,'appeal':False,'real_world_threat':False,'mass_bug':False,
            'draft_text':'Здравствуйте! Укажите время платежа. Нужна проверка администратора.','cited_ids':[],
            '_billing':{'estimated_cost_usd':.001,'provider':'groq'}}
        with patch.dict('os.environ',{'COPILOT_PROVIDER':'groq'}),patch('copilot.model.classify',return_value=(semantic,'accepted')):
            r=self.e.triage(self.ticket('Не получил приобретённую валюту'))
        self.assertEqual(r['priority'],'p0');self.assertTrue(r['needs_human'])
        self.assertEqual(r['audit']['generation_cost_usd'],.001)

    def test_semantic_invented_citation_falls_back(self):
        semantic={'category':'complaint.insult','lang':'ru','uncertain':False,
            'account_compromise':False,'payment':False,'appeal':False,'real_world_threat':False,'mass_bug':False,
            'draft_text':'Здравствуйте! Вы правы, применяем пункт 99.99.','cited_ids':['30:99.99'],
            '_billing':{'estimated_cost_usd':.001,'provider':'groq'}}
        with patch.dict('os.environ',{'COPILOT_PROVIDER':'groq'}),patch('copilot.model.classify',return_value=(semantic,'accepted')):
            r=self.e.triage(self.ticket('Он меня оскорбил','complaint'))
        self.assertEqual(r['audit']['draft_status'],'rejected_used_safe_template')
        self.assertNotIn('99.99',r['draft_reply']['text'])

    def test_does_not_ask_for_known_nickname_or_attachments(self):
        r=self.e.triage(self.ticket('Demo_Player оскорбил меня','complaint',images_count=1))
        self.assertNotIn('Уточните: ник игрока',r['draft_reply']['text'])
        self.assertNotIn('доказательства, если',r['draft_reply']['text'])

if __name__=='__main__':unittest.main()
