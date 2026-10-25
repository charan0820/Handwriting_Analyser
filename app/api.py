import asyncio
import io
import json
import multiprocessing as mp
import os
import re
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from app.imaging import MAX_BYTES, validate_image
from app.pipeline import assemble
from app.recognition import capabilities
from app.schemas import Settings, Edit, Rerun, Document
from app.store import Store, ROOT
from app.worker import worker_main
from src.evaluation.metrics import calculate_cer, calculate_wer

TERMINAL = ('completed','cancelled','failed')


def create_app(store=None, start_worker=True):
    store = store or Store()
    @asynccontextmanager
    async def lifespan(app):
        process = stop = None
        if start_worker:
            for job in store.list():
                if job['status']=='running':
                    store.update(job['id'],status='failed',stage='failed',
                                 error='Processing was interrupted. Completed lines were preserved; retry to continue.')
            context = mp.get_context('spawn')
            stop = context.Event()
            process = context.Process(target=worker_main,args=(str(store.root),stop),daemon=True)
            process.start()
            app.state.worker = process
        yield
        if stop:
            stop.set()
            process.join(timeout=3)
            if process.is_alive():
                process.terminate()
                process.join(timeout=3)

    app = FastAPI(title='Handwriting Analyser',version='1.0.0',lifespan=lifespan)

    @app.middleware('http')
    async def local_only(request: Request, call_next):
        # No cross-origin writes, including localhost DNS-rebinding protection.
        host = request.headers.get('host','').split(':')[0]
        if host not in ('localhost','127.0.0.1','testserver'):
            return Response('Use localhost to access this application.',status_code=403)
        origin = request.headers.get('origin')
        if request.method not in ('GET','HEAD','OPTIONS') and origin and origin != str(request.base_url).rstrip('/'):
            return Response('Cross-origin writes are disabled.',status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        return response

    def get_job(job_id):
        job = store.get(job_id)
        if job is None:
            raise HTTPException(404,'Document not found.')
        process = getattr(app.state,'worker',None)
        if process and not process.is_alive() and job['status'] in ('queued','running'):
            job = store.update(job_id,status='failed',stage='failed',
                               error='The inference worker stopped. Restart the application and retry; saved results remain available.')
        return job

    @app.get('/api/health')
    def health():
        worker = getattr(app.state,'worker',None)
        return {'status':'ok','worker_alive':worker.is_alive() if worker else False}

    @app.get('/api/models')
    def models():
        return capabilities()

    @app.get('/api/jobs')
    def list_jobs():
        return [{k:v for k,v in job.items() if k!='document'} for job in store.list()]

    @app.post('/api/jobs',status_code=202)
    async def create_job(file: UploadFile=File(...), settings: str=Form('{}'), title: str=Form('Untitled document')):
        try:
            options = Settings.model_validate_json(settings)
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        content = await file.read(MAX_BYTES+1)
        try:
            image = validate_image(content)
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        job_id = uuid.uuid4().hex
        folder = store.root/job_id
        folder.mkdir()
        (folder/'source.bin').write_bytes(content)
        image.save(folder/'original.png')
        job = dict(id=job_id,title=title.strip()[:160] or 'Untitled document',status='queued',stage='queued',
                   settings=options.model_dump(),created=time.time(),completed=0,total=0,
                   revision=0,document=None,error=None,cancel_requested=False,metrics=None)
        store.create(job)
        return job

    @app.get('/api/jobs/{job_id}')
    def detail(job_id: str):
        return get_job(job_id)

    @app.get('/api/jobs/{job_id}/events')
    async def events(job_id: str,request: Request):
        get_job(job_id)
        async def stream():
            previous = None
            while not await request.is_disconnected():
                job = get_job(job_id)
                encoded = json.dumps(job)
                if encoded != previous:
                    yield f'data: {encoded}\n\n'
                    previous = encoded
                else:
                    yield ': heartbeat\n\n'
                if job['status'] in TERMINAL:
                    break
                await asyncio.sleep(.6)
        return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache'})

    @app.post('/api/jobs/{job_id}/cancel')
    def cancel(job_id: str):
        job = get_job(job_id)
        if job['status'] in TERMINAL:
            return job
        return store.update(job_id,cancel_requested=True,**({'status':'cancelled','stage':'cancelled'} if job['status']=='queued' else {}))

    @app.post('/api/jobs/{job_id}/retry',status_code=202)
    def retry(job_id: str):
        job = get_job(job_id)
        if job['status'] not in TERMINAL:
            raise HTTPException(409,'Cancel the active job before retrying.')
        if job.get('document'):
            ids = [line['id'] for line in job['document']['lines'] if not line.get('raw_text')]
            # Retrying a partial result never overwrites completed or manually edited lines.
            if ids:
                return store.update(job_id,status='queued',stage='queued',rerun_ids=ids,cancel_requested=False,error=None)
            raise HTTPException(409,'All detected lines already have results. Select a line to rerun, or upload the page again.')
        return store.update(job_id,status='queued',stage='queued',cancel_requested=False,error=None)

    @app.patch('/api/jobs/{job_id}/document')
    def edit(job_id: str, edit: Edit):
        job = get_job(job_id)
        if not job.get('document'):
            raise HTTPException(409,'The page is not ready for editing yet.')
        document = Document.model_validate(job['document'])
        seen = set()
        original = {line.id:line for line in document.lines}
        for line in edit.lines:
            if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',line.id) or line.id in seen:
                raise HTTPException(422,'Line identifiers must be unique and contain letters, numbers, underscores or hyphens.')
            seen.add(line.id)
            for x,y in line.polygon:
                if not (0<=x<=document.width and 0<=y<=document.height):
                    raise HTTPException(422,'Line coordinates must be inside the prepared page.')
            # Client edits never change raw model evidence or model scores.
            if line.id in original:
                line.raw_text = original[line.id].raw_text
                line.score = original[line.id].score
                line.warnings = original[line.id].warnings
                line.baseline = original[line.id].baseline if line.polygon==original[line.id].polygon else None
            else:
                line.raw_text = ''
                line.score = None
                line.baseline = None
                line.warnings = ['New region. Rerun recognition to transcribe it.']
        document.lines = edit.lines
        document.settings.paragraph_mode = edit.paragraph_mode
        document.full_text = assemble([line.model_dump() for line in edit.lines],edit.paragraph_mode)
        metrics = None if edit.reference is None else {
            'cer':calculate_cer(document.full_text,edit.reference),'wer':calculate_wer(document.full_text,edit.reference)}
        updated = store.edit(job_id,edit.revision,edit.title,document.model_dump(),metrics,edit.reference)
        if updated is None:
            raise HTTPException(409,'This document changed or is processing. Reload it before saving.')
        return updated

    @app.post('/api/jobs/{job_id}/rerun',status_code=202)
    def rerun(job_id: str, data: Rerun):
        job = get_job(job_id)
        if job['status'] not in TERMINAL or not job.get('document'):
            raise HTTPException(409,'Finish or cancel processing before rerunning lines.')
        valid = {line['id'] for line in job['document']['lines']}
        if not set(data.line_ids)<=valid:
            raise HTTPException(422,'Selected line does not exist.')
        return store.update(job_id,status='queued',stage='queued',rerun_ids=data.line_ids,cancel_requested=False,error=None)

    @app.get('/api/jobs/{job_id}/image/{kind}')
    def image(job_id: str,kind: str):
        get_job(job_id)
        if kind not in ('original','page'):
            raise HTTPException(404,'Image not found.')
        path = store.root/job_id/f'{kind}.png'
        if not path.exists():
            raise HTTPException(404,'Prepared page is not available yet.')
        return FileResponse(path,media_type='image/png')

    @app.get('/api/jobs/{job_id}/export/{format}')
    def export(job_id: str,format: str):
        job = get_job(job_id)
        if not job.get('document'):
            raise HTTPException(409,'No transcription is available yet.')
        title = re.sub(r'[^a-zA-Z0-9 _-]','',job['title']).strip() or 'transcription'
        headers = {'Content-Disposition':f'attachment; filename="{title}.{format}"'}
        text = job['document']['full_text']
        if format=='txt':
            return Response(text,media_type='text/plain; charset=utf-8',headers=headers)
        if format=='docx':
            from docx import Document as WordDocument
            doc = WordDocument()
            doc.core_properties.title=job['title']
            for paragraph in text.split('\n\n'):
                doc.add_paragraph(paragraph)
            buffer=io.BytesIO()
            doc.save(buffer)
            return Response(buffer.getvalue(),headers=headers,
                media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        raise HTTPException(404,'Choose txt or docx.')

    @app.delete('/api/jobs/{job_id}',status_code=204)
    def delete(job_id: str):
        job = get_job(job_id)
        if job['status'] not in TERMINAL:
            raise HTTPException(409,'Cancel processing before deleting this document.')
        shutil.rmtree(store.root/job_id,ignore_errors=True)
        store.delete(job_id)
        return Response(status_code=204)

    @app.get('/api/sample')
    def sample():
        path=ROOT/'frontend/public/sample.json'
        if not path.exists():
            raise HTTPException(404,'Bundled sample is unavailable.')
        return json.loads(path.read_text(encoding='utf-8'))

    dist=ROOT/'frontend/dist'
    if dist.exists():
        app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
    return app


app=create_app()
