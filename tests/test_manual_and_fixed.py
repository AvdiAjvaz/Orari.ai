from fastapi.testclient import TestClient
from app.main import app,School,generate,verify

client=TestClient(app)

def school(**kwargs):
    data=dict(days=2,periods=2,teachers=[{'name':'A'},{'name':'B'}],lessons=[dict(classroom='C',subject='Math',teacher='A',hours=2),dict(classroom='C',subject='Science',teacher='B',hours=2)])
    data.update(kwargs);return School(**data)

def test_fixed_friday_sociology_survives_generation():
    s=school(days=5,periods=6,lessons=[dict(classroom='12',subject='Sociologji',teacher='A',hours=1,fixed_slots=[29]),dict(classroom='12',subject='Other',teacher='B',hours=5)])
    for _ in range(2):
        r=generate(s);assert r['verified']
        assert {'lesson':0,'slot':29} in r['entries']
        assert verify(s,r['entries'])==[]

def test_fixed_collision_and_teacher_availability_have_explanations():
    s=school(lessons=[dict(classroom='C',subject='X',teacher='A',hours=1,fixed_slots=[0]),dict(classroom='C',subject='Y',teacher='B',hours=1,fixed_slots=[0])])
    assert any('Orët statike përplasen' in e for e in generate(s)['issues'])
    s=school(teachers=[{'name':'A','unavailable':[0]},{'name':'B'}],lessons=[dict(classroom='C',subject='X',teacher='A',hours=1,fixed_slots=[0])])
    assert any('nuk është i disponueshëm' in e for e in generate(s)['issues'])

def test_invalid_fixed_slots_rejected():
    for slots in ([0,0],[9],[-1],[0,1,2]):
        data=school().model_dump();data['lessons'][0]['fixed_slots']=slots
        assert client.post('/api/generate',json=data).status_code==422

def test_validate_accepts_swap_but_rejects_teacher_conflict():
    s=school();entries=[dict(lesson=0,slot=0),dict(lesson=1,slot=1),dict(lesson=1,slot=2),dict(lesson=0,slot=3)]
    swapped=[dict(e) for e in entries];swapped[0]['slot']=1;swapped[1]['slot']=0
    response=client.post('/api/validate',json=dict(school=s.model_dump(),entries=swapped))
    assert response.json()['verified'] and response.json()['status']=='manual'
    s=school(lessons=[dict(classroom='C',subject='Math',teacher='A',hours=1),dict(classroom='D',subject='Science',teacher='A',hours=1)])
    response=client.post('/api/validate',json=dict(school=s.model_dump(),entries=[dict(lesson=0,slot=0),dict(lesson=1,slot=0)]))
    assert not response.json()['verified'] and any('Përplasje: A' in e for e in response.json()['issues'])

def test_manual_moves_and_exports_cannot_move_fixed_lesson():
    s=school(lessons=[dict(classroom='C',subject='Math',teacher='A',hours=2,fixed_slots=[0]),dict(classroom='C',subject='Science',teacher='B',hours=2)])
    entries=[dict(lesson=1,slot=0),dict(lesson=0,slot=1),dict(lesson=1,slot=2),dict(lesson=0,slot=3)]
    data=dict(school=s.model_dump(),entries=entries)
    assert any('ora statike' in e for e in verify(s,entries))
    assert not client.post('/api/validate',json=data).json()['verified']
    assert client.post('/api/export/xlsx',json=data).status_code==422

def test_manual_moves_cannot_create_gaps_or_break_double_periods():
    s=school(days=1,periods=3,lessons=[dict(classroom='C',subject='Math',teacher='A',hours=2)])
    data=dict(school=s.model_dump(),entries=[dict(lesson=0,slot=0),dict(lesson=0,slot=2)])
    assert not client.post('/api/validate',json=data).json()['verified']
    s=school(days=1,periods=3,lessons=[dict(classroom='C',subject='Math',teacher='A',hours=2,double_periods=1),dict(classroom='C',subject='Science',teacher='B',hours=1)])
    data=dict(school=s.model_dump(),entries=[dict(lesson=0,slot=0),dict(lesson=1,slot=1),dict(lesson=0,slot=2)])
    assert any('blloqet dyshe' in e for e in client.post('/api/validate',json=data).json()['issues'])
