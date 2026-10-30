import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from desktop import DesktopApi

class DesktopTests(unittest.TestCase):
    def test_first_start_without_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            app=DesktopApi(directory)
            self.assertEqual(app.health()['status'],'needs_rules')
            self.assertIn('error',app.triage({'kind':'report','messages':[]}))
            app._store.db.close()

    def test_queue_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            app=DesktopApi(directory)
            rows=[{'id':'custom-synthetic','text':'Синтетическая проверка'}]
            self.assertTrue(app.save_queue(rows)['saved']);app._store.db.close()
            other=DesktopApi(directory)
            self.assertEqual(other.load_queue(),rows);other._store.db.close()

    def test_key_stays_in_memory(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{},clear=True):
            app=DesktopApi(directory)
            key='gsk_synthetic_only_not_a_real_key'
            self.assertTrue(app.configure_groq(key)['configured'])
            self.assertEqual(os.environ['COPILOT_PROVIDER'],'groq')
            for path in Path(directory).rglob('*'):
                if path.is_file():self.assertNotIn(key.encode(),path.read_bytes())
            app.disconnect_groq();self.assertNotIn('GROQ_API_KEY',os.environ)
            app._store.db.close()

if __name__=='__main__':unittest.main()
