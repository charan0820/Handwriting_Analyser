"""Single separate process. SQLite is the durable queue and cancellation channel."""
import logging
import time
from app.store import Store
from app.schemas import Settings
from app.pipeline import run_document, Cancelled


def worker_main(root, stop):
    store = Store(root)
    while not stop.is_set():
        queued = [job for job in reversed(store.list()) if job['status']=='queued']
        if not queued:
            stop.wait(.4)
            continue
        job = queued[0]
        job_id = job['id']
        if job.get('cancel_requested'):
            store.update(job_id,status='cancelled',stage='cancelled')
            continue
        store.update(job_id,status='running',error=None)
        def progress(**fields):
            store.update(job_id,**fields)
        def cancelled():
            current = store.get(job_id)
            return stop.is_set() or current is None or current.get('cancel_requested',False)
        try:
            document = run_document(store.root/job_id,Settings.model_validate(job['settings']),progress,cancelled,
                                    existing=job.get('document') if job.get('rerun_ids') else None,
                                    selected=job.get('rerun_ids'))
            current = store.get(job_id)
            if current and current.get('cancel_requested'):
                raise Cancelled()
            store.update(job_id,status='completed',stage='completed',document=document,rerun_ids=None)
        except Cancelled:
            store.update(job_id,status='cancelled',stage='cancelled',error='Processing cancelled. Completed lines have been preserved.')
        except Exception as exc:
            logging.exception('Document %s failed',job_id)
            store.update(job_id,status='failed',stage='failed',error=str(exc))
