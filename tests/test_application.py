import io
import json
import threading
import zipfile
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.api import create_app
from app.store import Store
from app.schemas import Settings, Document, Line
from app.imaging import validate_image, prepare, split_long_line
from app.pipeline import run_document, Cancelled, assemble
from src.data.dataset import source_dataset_split, verified_writer_split
from src.training.train import text_to_indices


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path/'documents')


@pytest.fixture
def client(store):
    with TestClient(create_app(store,start_worker=False)) as client:
        yield client


def upload(client):
    buffer=io.BytesIO()
    Image.new('RGB',(300,200),'white').save(buffer,format='PNG')
    response=client.post('/api/jobs',files={'file':('notes.png',buffer.getvalue(),'image/png')},
                         data={'settings':json.dumps({'engine':'crnn','detector':'projection'}),'title':'Notes'})
    assert response.status_code==202,response.text
    return response.json()


def complete(store,job):
    line=Line(id='line-1',polygon=[(10,10),(200,10),(200,40),(10,40)],raw_text='raw word',text='raw word',score=.4)
    doc=Document(width=300,height=200,original_width=300,original_height=200,
                 transform=np.eye(3).tolist(),lines=[line],raw_text='raw word',full_text='raw word',settings=Settings())
    store.update(job['id'],status='completed',stage='completed',document=doc.model_dump())
    return doc.model_dump()


def test_validation_orientation_alpha_and_rejection(client):
    response=client.post('/api/jobs',files={'file':('bad.png',b'not an image','image/png')})
    assert response.status_code==422
    out=io.BytesIO()
    Image.new('RGBA',(20,30),(0,0,0,0)).save(out,format='PNG')
    image=validate_image(out.getvalue())
    assert image.mode=='RGB' and image.getpixel((1,1))==(255,255,255)
    out=io.BytesIO()
    original=Image.new('RGB',(20,30),'white')
    exif=original.getexif();exif[274]=6
    original.save(out,format='JPEG',exif=exif)
    assert validate_image(out.getvalue()).size==(30,20)
    assert client.post('/api/jobs',files={'file':('a.png',b'x','image/png')},data={'settings':'{"beam_width":99}'}).status_code==422


def test_edits_conflicts_exports_and_restart(client,store):
    job=upload(client);document=complete(store,job)
    document['lines'][0]['text']='Corrected café'
    document['lines'][0]['raw_text']='forged evidence'
    payload={'revision':0,'title':'Edited','lines':document['lines'],'paragraph_mode':'lines','reference':'Corrected café'}
    response=client.patch(f"/api/jobs/{job['id']}/document",json=payload)
    assert response.status_code==200,response.text
    saved=response.json()
    assert saved['document']['lines'][0]['raw_text']=='raw word'
    assert saved['metrics']=={'cer':0,'wer':0}
    assert client.patch(f"/api/jobs/{job['id']}/document",json=payload).status_code==409
    assert client.get(f"/api/jobs/{job['id']}/export/txt").text=='Corrected café'
    word=client.get(f"/api/jobs/{job['id']}/export/docx")
    with zipfile.ZipFile(io.BytesIO(word.content)) as archive:
        assert 'Corrected café' in archive.read('word/document.xml').decode()
    reopened=Store(store.root).get(job['id'])
    assert reopened['document']['full_text']=='Corrected café' and reopened['revision']==1


def test_queue_cancel_delete_and_origin(client,store):
    job=upload(client)
    assert client.delete(f"/api/jobs/{job['id']}").status_code==409
    cancelled=client.post(f"/api/jobs/{job['id']}/cancel").json()
    assert cancelled['status']=='cancelled'
    assert client.delete(f"/api/jobs/{job['id']}").status_code==204
    assert client.get(f"/api/jobs/{job['id']}").status_code==404
    assert client.post('/api/jobs/anything/cancel',headers={'Origin':'https://other.example'}).status_code==403
    assert client.get('/api/jobs',headers={'Host':'other.example'}).status_code==403


def test_invalid_regions_and_selective_rerun(client,store):
    job=upload(client);document=complete(store,job)
    assert client.post(f"/api/jobs/{job['id']}/rerun",json={'line_ids':['missing']}).status_code==422
    document['lines'][0]['polygon'][0]=[-1,0]
    assert client.patch(f"/api/jobs/{job['id']}/document",json={'revision':0,'title':'test','lines':document['lines']}).status_code==422
    document['lines'][0]['polygon'][0]=[10,10]
    document['lines'][0]['id']='../bad'
    assert client.patch(f"/api/jobs/{job['id']}/document",json={'revision':0,'title':'test','lines':document['lines']}).status_code==422
    assert client.post(f"/api/jobs/{job['id']}/rerun",json={'line_ids':['line-1']}).status_code==202
    assert store.get(job['id'])['rerun_ids']==['line-1']


def test_transform_and_long_line_pixel_coverage():
    page=Image.new('RGB',(200,100),'white')
    prepared,transform,_=prepare(page,Settings(deskew=False,rotation=90))
    assert prepared.size==(100,200)
    point=np.asarray(transform)@np.array([0,0,1])
    assert np.allclose(point,[99,0,1])
    with pytest.raises(ValueError):
        prepare(page,Settings(corners=[(0,0),(1,1),(1,0),(0,1)]))
    pixels=np.tile(np.arange(1000,dtype=np.uint16)%255,(20,1)).astype(np.uint8)
    line=Image.fromarray(pixels)
    pieces=split_long_line(line,max_ratio=8)
    assert np.array_equal(np.concatenate([np.array(p) for p in pieces],axis=1),pixels)


def test_deskew_accepts_hough_segments_in_both_shapes(monkeypatch):
    import cv2
    for shape in ((2,1,4),(2,4)):
        segments=np.array([[0,10,150,12],[0,40,150,42]],dtype=np.int32).reshape(shape)
        monkeypatch.setattr(cv2,'HoughLinesP',lambda *args,**kwargs:segments)
        page,transform,_=prepare(Image.new('RGB',(200,100),'white'),Settings())
        assert page.width>=200 and page.height>=100 and len(transform)==3


def test_pipeline_partial_result_and_cancellation(tmp_path,monkeypatch):
    Image.new('RGB',(300,200),'white').save(tmp_path/'original.png')
    import app.pipeline as pipeline
    monkeypatch.setattr(pipeline,'detect_lines',lambda image,detector:[[(5,5),(200,5),(200,40),(5,40)],[(5,80),(200,80),(200,110),(5,110)]])
    class FakeRecognizer:
        device='cpu'
        def __init__(self,engine): pass
        def recognize(self,image,settings): return 'recognized',.8,[]
    monkeypatch.setattr(pipeline,'Recognizer',FakeRecognizer)
    updates=[]
    document=run_document(tmp_path,Settings(),lambda **fields:updates.append(fields),lambda:False)
    assert document['raw_text']=='recognized\nrecognized'
    assert any(item.get('completed')==1 and item.get('document') for item in updates)
    with pytest.raises(Cancelled):
        run_document(tmp_path,Settings(),lambda **fields:None,lambda:True)


def test_source_partitions_and_authoritative_writer_groups():
    paths=['train_1.png','validation_1.png','test_1.png']
    split=source_dataset_split(paths,['a','b','c'])
    assert [part[0] for part in split]==[['train_1.png'],['validation_1.png'],['test_1.png']]
    with pytest.raises(ValueError): source_dataset_split(['a01-001-00.png'],['a'])
    with pytest.raises(ValueError): verified_writer_split(paths,['a','b','c'],{})
    with pytest.raises(ValueError): text_to_indices('é',{'chars':['a']})


def test_layout_recall_and_order_are_measured_from_annotations():
    from src.evaluation.layout import evaluate_layout
    top=[(10,10),(90,10),(90,25),(10,25)]
    bottom=[(10,50),(90,50),(90,65),(10,65)]
    result=evaluate_layout([bottom,top],[top,bottom],(100,100))
    assert result['line_recall']==1 and result['reading_order_inversions']==1
    partial=evaluate_layout([top],[top,bottom],(100,100))
    assert partial['line_recall']==.5


def test_recognizer_retries_gpu_exhaustion_on_cpu(monkeypatch):
    import torch
    from app.recognition import Recognizer
    recognizer=Recognizer.__new__(Recognizer)
    recognizer.device='cuda'
    recognizer.startup_warnings=[]
    moves=[]
    class Model:
        def to(self,device): moves.append(device);return self
    recognizer.model=Model()
    attempts=[]
    def predict(image,settings,notes):
        attempts.append(recognizer.device)
        if len(attempts)==1:
            raise torch.cuda.OutOfMemoryError('simulated allocation failure')
        return 'recovered',.8,notes
    monkeypatch.setattr(recognizer,'_recognize',predict)
    text,score,notes=recognizer.recognize(Image.new('RGB',(10,10),'white'),Settings())
    assert text=='recovered' and moves==['cpu'] and attempts==['cuda','cpu']
    assert any('memory' in note for note in notes)


def test_wide_upload_cannot_expand_kraken_tensor_width():
    from app.recognition import detection_canvas
    # The reported input previously became ~19,660 x 1800 inside Kraken.
    for size in ((1398,128),(12000,40),(128,1398),(1200,720),(1,10000)):
        image=Image.new('RGB',size,'white')
        canvas,scale,offset=detection_canvas(image)
        internal_width=round(1800*canvas.width/canvas.height)
        assert internal_width<=1800
        assert max(canvas.size)<=2400
    strip=Image.new('RGB',(1398,128),'black')
    canvas,scale,(ox,oy)=detection_canvas(strip)
    assert scale==1
    # Detection-only padding preserves every source pixel and its aspect ratio.
    assert np.array_equal(np.array(canvas.crop((ox,oy,ox+1398,oy+128))),np.array(strip))


def test_detected_regions_map_back_from_padding_and_downsampling():
    from types import SimpleNamespace
    from app.recognition import detection_canvas,map_detected_region
    image=Image.new('RGB',(4800,400),'white')
    canvas,scale,(ox,oy)=detection_canvas(image)
    source=np.array([[20,10],[4780,10],[4780,390],[20,390]],float)
    baseline=np.array([[20,300],[4780,300]],float)
    line=SimpleNamespace(boundary=(source*scale+[ox,oy]).tolist(),
                         baseline=(baseline*scale+[ox,oy]).tolist())
    mapped=map_detected_region(line,image,scale,(ox,oy))
    assert np.allclose(mapped['polygon'],source)
    assert np.allclose(mapped['baseline'],baseline)
    padding_line=SimpleNamespace(boundary=[[0,0],[200,0],[200,20],[0,20]],baseline=[[0,10],[200,10]])
    assert map_detected_region(padding_line,image,scale,(ox,oy)) is None


def test_wide_single_line_shortcut_preserves_multiline_detection():
    from app.recognition import single_line_region,detect_lines
    from PIL import ImageDraw
    strip=Image.new('RGB',(1400,150),'white')
    draw=ImageDraw.Draw(strip)
    for x in range(30,1350,40):
        draw.rectangle((x,35,x+20,115),fill='black')
    region=single_line_region(strip)
    assert region==[(0,0),(1399,0),(1399,149),(0,149)]
    # This path does not load Kraken or create any segmentation tensors.
    assert detect_lines(strip,'kraken')==[region]
    multiline=Image.new('RGB',(1400,150),'white')
    draw=ImageDraw.Draw(multiline)
    for y in (15,90):
        for x in range(30,1350,40):
            draw.rectangle((x,y,x+20,y+35),fill='black')
    assert single_line_region(multiline) is None
    assert single_line_region(Image.new('RGB',(1400,150),'white')) is None
