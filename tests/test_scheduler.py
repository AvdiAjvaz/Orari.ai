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
    assert len(result['entries'])==4 and result['penalty']==1
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

def test_teacher_weekly_cap_is_strict_across_classes():
    s=school(teachers=[{'name':'A','max_hours':3}],lessons=[{'classroom':'C','subject':'X','teacher':'A','hours':2},{'classroom':'D','subject':'Y','teacher':'A','hours':2}])
    result=generate(s)
    assert result['status']=='infeasible'
    assert any('maksimumi javor është 3' in issue for issue in result['issues'])
    assert any('maksimumi javor' in e for e in verify(s,[{'lesson':0,'slot':0},{'lesson':0,'slot':1},{'lesson':1,'slot':2},{'lesson':1,'slot':3}]))

def test_exact_weekly_cap_and_allowed_days_hours():
    s=school(days=5,periods=6,teachers=[{'name':'A','max_hours':4,'unavailable':[d*6+p for d in range(5) for p in range(6) if d not in [1,3] or p<2]},{'name':'B','unavailable':[d*6+p for d in range(5) for p in range(6) if d not in [1,3] or p>=2]}],lessons=[{'classroom':'C','subject':'X','teacher':'A','hours':4},{'classroom':'C','subject':'Y','teacher':'B','hours':4}])
    result=generate(s)
    assert result['verified'] and len(result['entries'])==8
    assert all(e['slot']//6 in [1,3] and e['slot']%6>=2 for e in result['entries'] if e['lesson']==0)

def test_invalid_and_zero_weekly_cap():
    data=school().model_dump();data['teachers'][0]['max_hours']=-1
    assert client.post('/api/generate',json=data).status_code==422
    data['teachers'][0]['max_hours']=0
    assert client.post('/api/generate',json=data).json()['status']=='infeasible'


def test_class_cannot_start_late_or_have_internal_holes():
    for blocked in ([0], [1]):
        s=school(days=1,periods=3,teachers=[{'name':'A','unavailable':blocked}],lessons=[{'classroom':'C','subject':'X','teacher':'A','hours':2}])
        assert generate(s)['status']=='infeasible'
        entries=[{'lesson':0,'slot':slot} for slot in range(3) if slot not in blocked]
        assert any('pa orë të zbrazëta' in message for message in verify(s,entries))

def test_every_generated_class_day_is_a_prefix():
    s=school(days=5,periods=6,teachers=[{'name':'A'},{'name':'B'}],lessons=[{'classroom':'C','subject':'X','teacher':'A','hours':4},{'classroom':'C','subject':'Y','teacher':'B','hours':7},{'classroom':'D','subject':'X','teacher':'A','hours':5}])
    result=generate(s);assert result['verified']
    for classroom in ['C','D']:
        for day in range(s.days):
            periods=sorted(e['slot']%s.periods for e in result['entries'] if s.lessons[e['lesson']].classroom==classroom and e['slot']//s.periods==day)
            assert periods==list(range(len(periods)))
