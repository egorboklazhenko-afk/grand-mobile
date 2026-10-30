"""Windows application entry point. UI talks directly to Python, without a browser server."""
import json
import os
import sys
import tarfile
import threading
from pathlib import Path
from copilot.engine import Engine
from copilot.model import enabled
from copilot.state import Store

RESOURCE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
HOME=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent

class DesktopApi:
    def __init__(self,home=HOME):
        self._home=Path(home)
        self._runtime=self._home/'user-data'
        self._runtime.mkdir(exist_ok=True)
        self._store=Store(str(self._runtime/'copilot.sqlite3'))
        self._engine=None
        self._lock=threading.RLock()
        self._window=None
        path=self._home/'data'/'rules.json'
        if path.exists():self._engine=Engine(path,self._store)

    def health(self):
        return {'status':'ok' if self._engine else 'needs_rules',
            'rule_points':len(self._engine.index.points) if self._engine else 0,
            'provider':'groq' if os.getenv('COPILOT_PROVIDER')=='groq' else 'ollama' if os.getenv('OLLAMA_MODEL') else 'offline',
            'model_enabled':enabled(),'key_configured':bool(os.getenv('GROQ_API_KEY'))}

    def triage(self,body):
        if not self._engine:return {'error':'Сначала загрузите правила: Настройки → Загрузить архив кейса.'}
        try:
            with self._lock:return self._engine.triage(body)
        except Exception:return {'error':'Не удалось обработать обращение. Проверьте формат входных данных.'}

    def feedback(self,body):
        if not isinstance(body,dict) or body.get('action') not in ('approve_draft','edit','escalate'):
            return {'error':'Некорректное действие'}
        return {'saved':True,'feedback_id':self._store.feedback(body),'delivered_to_player':False}

    def configure_groq(self,key,model='openai/gpt-oss-120b'):
        if not isinstance(key,str) or not 10<len(key.strip())<500 or any(c.isspace() for c in key.strip()):
            return {'error':'Введите API-ключ из консоли Groq.'}
        if model not in ('openai/gpt-oss-120b',):return {'error':'Эта сборка настроена на openai/gpt-oss-120b.'}
        with self._lock:
            os.environ['GROQ_API_KEY']=key.strip();os.environ['COPILOT_PROVIDER']='groq';os.environ['GROQ_MODEL']=model
            os.environ['GROQ_INPUT_USD_PER_M']='0.15';os.environ['GROQ_OUTPUT_USD_PER_M']='0.60'
        return {'configured':True,'provider':'groq','stored_on_disk':False}

    def disconnect_groq(self):
        with self._lock:
            os.environ.pop('GROQ_API_KEY',None);os.environ.pop('COPILOT_PROVIDER',None)
        return {'configured':False,'provider':'offline'}

    def import_rules(self):
        import webview
        paths=self._window.create_file_dialog(webview.FileDialog.OPEN,file_types=('Grand case (*.tgz;*.gz;*.json)',))
        if not paths:return {'cancelled':True}
        try:
            source=Path(paths[0])
            if source.suffix=='.json':raw=source.read_bytes()
            else:
                with tarfile.open(source,'r:gz') as archive:
                    member=archive.getmember('handout/rules.json')
                    if not member.isfile() or member.size>8*1024*1024:raise ValueError()
                    with archive.extractfile(member) as f:raw=f.read()
            parsed=json.loads(raw)
            if not isinstance(parsed.get('rules'),list):raise ValueError()
            directory=self._home/'data';directory.mkdir(exist_ok=True)
            path=directory/'rules.json'
            # Validate before replacing a working index.
            temporary=directory/'rules.pending.json';temporary.write_bytes(raw)
            candidate=Engine(temporary,self._store)
            temporary.replace(path)
            with self._lock:self._engine=candidate
            return {'loaded':True,'rule_points':len(candidate.index.points)}
        except Exception:return {'error':'В файле не найдены корректные правила Support Copilot.'}

    def save_queue(self,rows):
        if not isinstance(rows,list) or len(rows)>1000:return {'error':'Не более 1000 обращений'}
        data=json.dumps(rows,ensure_ascii=False)
        if len(data)>5_000_000:return {'error':'Очередь слишком большая'}
        path=self._runtime/'queue.json'
        temporary=path.with_suffix('.pending');temporary.write_text(data,encoding='utf-8');temporary.replace(path)
        return {'saved':True}

    def load_queue(self):
        path=self._runtime/'queue.json'
        try:return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        except Exception:return []

def main():
    import webview
    api=DesktopApi()
    html=(RESOURCE/'web'/'index.html').read_text(encoding='utf-8')
    html=html.replace('</head>','<script>window.GRAND_DESKTOP=true;</script></head>')
    script=(RESOURCE/'web'/'app.js').read_text(encoding='utf-8')
    html=html.replace('<script src="/app.js"></script>','<script>'+script+'</script>')
    window=webview.create_window('Grand Copilot — рабочее место поддержки',html=html,js_api=api,
        width=1380,height=900,min_size=(1000,680),background_color='#0d1117',text_select=True)
    api._window=window
    webview.start(gui='edgechromium',debug=False,private_mode=True)
    os.environ.pop('GROQ_API_KEY',None)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Show an actionable startup error even in the console-free .exe build.
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,'Не удалось запустить Grand Copilot.\n\n'+str(exc)+'\n\nДля интерфейса требуется Microsoft Edge WebView2 Runtime.','Grand Copilot',0x10)
