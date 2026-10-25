"""SQLite-backed jobs; every worker update preserves cancellation requests."""
import json
import os
import sqlite3
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_USER_DATA = (Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData'/'Local')) if sys.platform=='win32'
              else Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local'/'share')))
DATA = Path(os.environ.get('HTR_DATA_DIR', _USER_DATA / 'handwriting-analyser' / 'documents')).resolve()


class Store:
    def __init__(self, root=DATA):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / 'jobs.sqlite3'
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('''CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated REAL NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS revisions (
                job_id TEXT, revision INTEGER, document TEXT, created REAL,
                PRIMARY KEY(job_id, revision))''')

    def connect(self):
        return sqlite3.connect(self.database, timeout=30)

    def get(self, job_id):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM jobs WHERE id=?', (job_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self):
        with self.connect() as db:
            rows = db.execute('SELECT payload FROM jobs ORDER BY updated DESC').fetchall()
        return [json.loads(row[0]) for row in rows]

    def create(self, job):
        with self.connect() as db:
            db.execute('INSERT INTO jobs VALUES (?,?,?)', (job['id'], json.dumps(job), time.time()))

    def update(self, job_id, **fields):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not row:
                return None
            job = json.loads(row[0])
            job.update(fields)
            db.execute('UPDATE jobs SET payload=?, updated=? WHERE id=?',
                       (json.dumps(job), time.time(), job_id))
        return job

    def edit(self, job_id, revision, title, document, metrics, reference=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM jobs WHERE id=?', (job_id,)).fetchone()
            job = json.loads(row[0]) if row else None
            if not job or job['revision'] != revision or job['status'] not in ('completed', 'failed', 'cancelled'):
                return None
            job.update(revision=revision + 1, title=title, document=document, metrics=metrics, reference=reference)
            db.execute('INSERT INTO revisions VALUES (?,?,?,?)',
                       (job_id, job['revision'], json.dumps(document), time.time()))
            db.execute('UPDATE jobs SET payload=?, updated=? WHERE id=?', (json.dumps(job), time.time(), job_id))
        return job

    def delete(self, job_id):
        with self.connect() as db:
            db.execute('DELETE FROM revisions WHERE job_id=?', (job_id,))
            db.execute('DELETE FROM jobs WHERE id=?', (job_id,))
