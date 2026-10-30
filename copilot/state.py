import datetime as dt
import hashlib
import json
import sqlite3
import threading
import re

class Store:
    def __init__(self, path=':memory:'):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.RLock()
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS seen (scope TEXT, fingerprint TEXT, time REAL, ticket TEXT);
          CREATE INDEX IF NOT EXISTS seen_lookup ON seen(scope, fingerprint, time);
          CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, time TEXT, payload TEXT);
        ''')

    def duplicate(self, scope, text, when, ticket_id=None):
        if not scope or not text:
            return False
        try:
            stamp = dt.datetime.fromisoformat(when.replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=dt.timezone.utc)
            timestamp = stamp.timestamp()
        except (ValueError, AttributeError):
            return False
        canonical=' '.join(re.findall(r'\w+',text.lower()))
        fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
        with self.lock, self.db:
            row = self.db.execute('SELECT ticket FROM seen WHERE scope=? AND fingerprint=? AND time BETWEEN ? AND ? LIMIT 1',
                                  (scope, fingerprint, timestamp-3600, timestamp)).fetchone()
            same = row is not None and (not ticket_id or row[0] != ticket_id)
            if row is None or row[0] != ticket_id:
                self.db.execute('INSERT INTO seen VALUES(?,?,?,?)', (scope, fingerprint, timestamp, ticket_id))
            return same

    def feedback(self, payload):
        with self.lock, self.db:
            cur = self.db.execute('INSERT INTO feedback(time,payload) VALUES(?,?)',
                (dt.datetime.now(dt.timezone.utc).isoformat(), json.dumps(payload, ensure_ascii=False)))
            return cur.lastrowid
