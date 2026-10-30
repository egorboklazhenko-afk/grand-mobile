import io
import json
import unittest
from unittest.mock import patch
from copilot.model import request_model

class Response(io.BytesIO):
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

class TransportTests(unittest.TestCase):
    def test_groq_schema_usage_and_secret_header(self):
        payload={'choices':[{'message':{'content':'{"ok":true}'}}],
                 'usage':{'prompt_tokens':800,'completion_tokens':200}}
        with patch.dict('os.environ',{'COPILOT_PROVIDER':'groq','GROQ_API_KEY':'synthetic-test-secret','GROQ_MODEL':'openai/gpt-oss-120b'}),patch('urllib.request.urlopen',return_value=Response(json.dumps(payload).encode())) as send:
            out,usage=request_model([{'role':'user','content':'synthetic example'}],{'type':'object','properties':{}})
        self.assertTrue(out['ok']);self.assertAlmostEqual(usage['estimated_cost_usd'],.00024)
        req=send.call_args.args[0]
        self.assertEqual(req.full_url,'https://api.groq.com/openai/v1/chat/completions')
        self.assertNotIn(b'synthetic-test-secret',req.data)
        self.assertEqual(json.loads(req.data)['response_format']['type'],'json_schema')

    def test_missing_key_makes_no_request(self):
        with patch.dict('os.environ',{'COPILOT_PROVIDER':'groq','GROQ_API_KEY':''}),patch('urllib.request.urlopen') as send:
            with self.assertRaises(ValueError):request_model([], {})
            send.assert_not_called()

if __name__=='__main__':unittest.main()
