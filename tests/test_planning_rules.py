from fastapi.testclient import TestClient
from app.main import app, School, generate, verify

client=TestClient(app)

def fixture(**kwargs):
    data=dict(days=2,periods=4,teachers=[{'name':'A'},{'name':'B'}],lessons=[dict(classroom='C',subject='Math',teacher='A',hours=4)])
    data.update(kwargs)
    return School(**data)

def test_daily_bounds_and_class_specific_override():
    s=fixture(min_daily_hours=2,max_daily_hours=3,class_rules=[dict(classroom='D',min_daily_hours=1,max_daily_hours=1)],lessons=[dict(classroom='C',subject='Math',teacher='A',hours=5),dict(classroom='D',subject='Science',teacher='B',hours=2)])
    r=generate(s);assert r['verified']
    loads={(c,d):sum(s.lessons[e['lesson']].classroom==c and e['slot']//4==d for e in r['entries']) for c in ['C','D'] for d in range(2)}
    assert sorted(loads['C',d] for d in range(2))==[2,3]
    assert [loads['D',d] for d in range(2)]==[1,1]
    assert verify(s,r['entries'])==[]

def test_daily_minimum_is_for_every_day_and_capacity_explained():
    s=fixture(min_daily_hours=3)
    r=generate(s);assert r['status']=='infeasible'
    assert any('kufijtë 3–4' in issue for issue in r['issues'])
    s=fixture(min_daily_hours=2,max_daily_hours=2)
    bad=[dict(lesson=0,slot=p) for p in range(4)]
    assert any('ngarkesa ditore' in error for error in verify(s,bad))

def test_subject_limit_aggregates_across_teachers():
    s=fixture(max_subject_per_day=1,lessons=[dict(classroom='C',subject='Math',teacher='A',hours=2),dict(classroom='C',subject='Math',teacher='B',hours=2)])
    assert generate(s)['status']=='infeasible'
    assert any('kufiri' in error for error in verify(s,[dict(lesson=0,slot=0),dict(lesson=1,slot=1),dict(lesson=0,slot=4),dict(lesson=1,slot=5)]))

def test_double_blocks_and_subject_override():
    s=fixture(max_subject_per_day=1,lessons=[dict(classroom='C',subject='Math',teacher='A',hours=4,max_per_day=2,double_periods=2)])
    r=generate(s);assert r['verified']
    assert sorted(e['slot'] for e in r['entries'])==[0,1,4,5]
    assert verify(s,r['entries'])==[]
    s=fixture(max_subject_per_day=1,lessons=[dict(classroom='C',subject='Math',teacher='A',hours=4,double_periods=2)])
    r=generate(s);assert r['status']=='infeasible'
    assert any('blloqet dyshe' in issue for issue in r['issues'])

def test_pairs_cannot_cross_day_boundaries():
    s=fixture(periods=3,teachers=[{'name':'A','unavailable':[0,1,4,5]},{'name':'B'}],lessons=[dict(classroom='C',subject='Math',teacher='A',hours=2,double_periods=1),dict(classroom='C',subject='Science',teacher='B',hours=4)])
    assert generate(s)['status']=='infeasible'
    entries=[dict(lesson=0,slot=s) for s in [2,3]]+[dict(lesson=1,slot=s) for s in [0,1,4,5]]
    assert any('blloqet dyshe' in error for error in verify(s,entries))

def test_pairs_must_be_disjoint_and_odd_hours_supported():
    s=fixture(days=1,periods=5,lessons=[dict(classroom='C',subject='Math',teacher='A',hours=4,double_periods=2),dict(classroom='C',subject='Science',teacher='B',hours=1)])
    bad=[dict(lesson=0,slot=p) for p in [0,1,2,4]]+[dict(lesson=1,slot=3)]
    assert any('blloqet dyshe' in error for error in verify(s,bad))
    s=fixture(lessons=[dict(classroom='C',subject='Math',teacher='A',hours=3,double_periods=1)])
    assert generate(s)['verified']

def test_invalid_rule_combinations_rejected():
    for changes in [dict(min_daily_hours=3,max_daily_hours=2),dict(class_rules=[dict(classroom='C',min_daily_hours=4,max_daily_hours=2)]),dict(lessons=[dict(classroom='C',subject='Math',teacher='A',hours=3,double_periods=2)])]:
        data=fixture().model_dump();data.update(changes)
        assert client.post('/api/generate',json=data).status_code==422

def test_exports_enforce_new_rules():
    s=fixture(max_subject_per_day=1)
    data=dict(school=s.model_dump(),entries=[dict(lesson=0,slot=p) for p in [0,1,4,5]])
    assert client.post('/api/export/xlsx',json=data).status_code==422

def test_unknown_photo_subject_is_not_assumed_to_be_one_real_subject():
    s=fixture(max_subject_per_day=1,lessons=[dict(classroom='C',subject='Lëndë e papërcaktuar',teacher='A',hours=4)])
    assert generate(s)['verified']

def test_daily_minimum_also_applies_to_registered_classes_without_lessons():
    s=fixture(classes=['C','Empty'],min_daily_hours=1)
    result=generate(s)
    assert result['status']=='infeasible'
    assert any('Empty' in message for message in result['issues'])
