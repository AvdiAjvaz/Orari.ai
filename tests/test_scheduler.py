from fastapi.testclient import TestClient
from app.main import app, School, generate, verify

client = TestClient(app)

def school(**kwargs):
    data = dict(days=2, periods=2, teachers=[{'name':'A', 'unavailable':[0]}, {'name':'B'}], lessons=[{'classroom':'VI-1','subject':'Math','teacher':'A','hours':2},{'classroom':'VI-2','subject':'Science','teacher':'B','hours':2,'room':'Lab'}])
    data.update(kwargs)
    return School(**data)

def test_valid_schedule_and_spreading():
    s=school(); result=generate(s)
    assert result['verified'] and result['status']=='optimal'
    assert len(result['entries'])==4 and result['penalty']==0
    assert verify(s,result['entries'])==[]

def test_capacity_failure():
    s=school(days=1,periods=2)
    assert generate(s)['status']=='infeasible'

def test_combined_unavailability_conflict():
    s=school(days=1,periods=2,teachers=[{'name':'A','unavailable':[0]},{'name':'B','unavailable':[0]}],lessons=[{'classroom':'C','subject':'X','teacher':'A','hours':1},{'classroom':'C','subject':'Y','teacher':'B','hours':1}])
    assert generate(s)['status']=='infeasible'

def test_room_exclusivity():
    s=school(teachers=[{'name':'A'},{'name':'B'}],lessons=[{'classroom':'C','subject':'X','teacher':'A','hours':2,'room':'Lab'},{'classroom':'D','subject':'Y','teacher':'B','hours':2,'room':'Lab'}])
    result=generate(s)
    assert result['verified']
    assert len({e['slot'] for e in result['entries']})==4

def test_verifier_rejects_corrupted_result():
    s=school()
    assert verify(s,[{'lesson':0,'slot':0},{'lesson':0,'slot':0}])
    assert verify(s,[{'lesson':999,'slot':0}])

def test_api_and_ui():
    assert client.get('/api/health').json()=={'status':'ok'}
    assert 'Java shkollore' in client.get('/').text
    response=client.post('/api/generate',json=school().model_dump())
    assert response.status_code==200 and response.json()['verified']
    data=school().model_dump();data['lessons'][0]['teacher']='missing'
    assert client.post('/api/generate',json=data).status_code==422
