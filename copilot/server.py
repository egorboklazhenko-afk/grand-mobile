"""Loopback-only demonstration HTTP server. Not a production internet gateway."""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .engine import Engine
from .state import Store
from .model import enabled

ROOT=Path(__file__).resolve().parent.parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--host',default='127.0.0.1')
    args=parser.parse_args()
    Path('runtime').mkdir(exist_ok=True)
    store=Store('runtime/copilot.sqlite3')
    engine=Engine(os.getenv('RULES_PATH','data/rules.json'),store)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,fmt,*args): pass  # No ticket text or identifiers in access logs.

        def send(self,status,payload,ctype='application/json; charset=utf-8'):
            data=payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type',ctype)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            if self.path=='/health':
                return self.send(200,{'status':'ok','rule_points':len(engine.index.points),'mode':'local_service','provider':os.getenv('COPILOT_PROVIDER','ollama' if os.getenv('OLLAMA_MODEL') else 'offline'),'model_enabled':enabled()})
            files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8')}
            if self.path in files:
                name,ctype=files[self.path]
                return self.send(200,(ROOT/'web'/name).read_bytes(),ctype)
            self.send(404,{'error':'not_found'})

        def do_POST(self):
            # Reject cross-origin browser writes; no CORS, no remote deployment.
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}'):
                return self.send(403,{'error':'origin_not_allowed'})
            if self.path not in ('/triage','/feedback'):
                return self.send(404,{'error':'not_found'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<=0 or size>256000: return self.send(413,{'error':'request_size'})
                body=json.loads(self.rfile.read(size))
                if not isinstance(body,dict): raise ValueError('JSON object required')
                if self.path=='/triage': return self.send(200,engine.triage(body))
                if body.get('action') not in ('approve_draft','edit','escalate'):
                    raise ValueError('invalid feedback action')
                if not isinstance(body.get('edited_text',''),str) or len(body.get('edited_text',''))>10000:
                    raise ValueError('invalid edited_text')
                return self.send(200,{'saved':True,'feedback_id':store.feedback(body),'delivered_to_player':False})
            except (ValueError,TypeError,KeyError) as exc:
                self.send(400,{'error':str(exc)})
            except Exception:
                self.send(500,{'error':'internal_error'})

    server=ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'Grand Copilot: http://{args.host}:{args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
