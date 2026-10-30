"""Hand-authored synthetic scenarios. Not the hidden competition test."""
import json
import unittest
from pathlib import Path
import test_engine as fixtures
from copilot.engine import Engine
from copilot.model import request_model
from unittest.mock import patch

CASES=[
 ('report','Пропала машина из гаража','report.account','p2','ru'),
 ('report','Взломали аккаунт','report.account','p0','ru'),
 ('report','Не могу войти в игру','report.account','p0','ru'),
 ('report','Оплатил донат, не пришли ГК','report.payment','p0','ru'),
 ('report','Застрял в текстурах','report.help','p2','ru'),
 ('report','Помогите выбраться из ямы','report.help','p2','ru'),
 ('report','Где взять лицензию?','report.question','p3','ru'),
 ('report','Подскажите, как устроиться в полицию','report.question','p3','ru'),
 ('report','привет','report.offtopic','p3','ru'),
 ('report','Меня дмят у спавна','report.complaint','p2','ru'),
 ('report','Игрок оскорбляет меня','report.complaint','p2','ru'),
 ('complaint','Читер стреляет через стены','complaint.cheat','p1','ru'),
 ('complaint','Он взял деньги за машину и не отдал','complaint.scam','p3','ru'),
 ('complaint','Вымогает миллион за возврат машины','complaint.scam','p1','ru'),
 ('complaint','Продаёт аккаунт за реал','complaint.rmt_ads','p1','ru'),
 ('complaint','Админ выдал мут без причины','complaint.admin','p3','ru'),
 ('complaint','Как купить дом?','complaint.invalid','p3','ru'),
 ('complaint','Demo_Player оскорбил меня','complaint.insult','p3','ru'),
 ('complaint','Игрок убил меня без причины','complaint.dm','p3','ru'),
 ('report','Please help my account was hacked','report.account','p0','en'),
 ('report','How can I get a license?','report.question','p3','en'),
 ('report','I am stuck in a wall, please help','report.help','p2','en'),
 ('report','My payment was not received','report.payment','p0','en'),
 ('report','Сәлеметсіз бе, аккаунтым бұзылды','report.account','p0','kk'),
 ('report','Қалай жұмысқа тұруға болады?','report.question','p3','kk'),
 ('report','Төлем жасадым, ақша түспеді','report.payment','p0','kk'),
 ('report','Salom, to‘lov qildim, pulim kelmadi','report.payment','p0','uz'),
 ('report','Salom, akkauntim buzildi, yordam bering','report.account','p0','uz'),
 ('report','Qanday litsenziya olish mumkin?','report.question','p3','uz'),
 ('report','Salom, qotib qoldim, yordam bering','report.help','p2','uz'),
 ('report','Hola, necesito ayuda con un pago','report.payment','p0','es'),
 ('report','Olá, meu pagamento não chegou','report.payment','p0','pt'),
]

class SubmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.TestEngine.setUpClass()
    @classmethod
    def tearDownClass(cls):fixtures.TestEngine.tearDownClass()

    def test_synthetic_triage_matrix(self):
        engine=Engine(fixtures.TestEngine.rules)
        for kind,text,category,priority,lang in CASES:
            with self.subTest(text=text):
                r=engine.triage({'kind':kind,'messages':[{'role':'player','text':text}]})
                self.assertEqual(r['category'],category)
                self.assertEqual(r['priority'],priority)
                self.assertEqual(r['lang'],lang)

    def test_cost_allowance_rejects_long_request_without_network(self):
        with patch.dict('os.environ',{'COPILOT_PROVIDER':'groq','GROQ_API_KEY':'synthetic-test-secret'}),patch('urllib.request.urlopen') as send:
            with self.assertRaisesRegex(ValueError,'cost_allowance'):request_model([{'role':'user','content':'я'*20000}],{})
            send.assert_not_called()

    def test_server_nickname_and_link_extraction(self):
        r=Engine(fixtures.TestEngine.rules).triage({'kind':'complaint','messages':[{'role':'player','text':'Demo_Player оскорбил меня на сервере 17: https://example.test/video'}]})
        self.assertEqual(r['extracted']['server'],'17')
        self.assertEqual(r['extracted']['nickname'],'Demo_Player')
        self.assertTrue(r['extracted']['has_evidence'])

    def test_punctuation_duplicate(self):
        engine=Engine(fixtures.TestEngine.rules)
        row={'kind':'report','reporter_hash':'synthetic','created_at':'2026-10-30T10:00:00','messages':[{'role':'player','text':'Застрял в текстурах!'}]}
        engine.triage(row)
        row['messages'][0]['text']='Застрял  в текстурах.'
        self.assertTrue(engine.triage(row)['audit']['duplicate'])
