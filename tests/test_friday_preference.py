from app.main import School,generate,verify
from app.examples import photo_example


def test_photo_example_prefers_six_hours_and_can_achieve_it():
    example=photo_example();state=example['state']
    assert state['preferredFriday']==6
    school=School(**{**state,'teachers':[{'name':t['name']} for t in state['teachers']],'preferred_friday_hours':6})
    result=generate(school)
    assert result['verified'] and len(result['entries'])==199
    assert result['friday_deviation']==0 and set(result['friday_loads'].values())=={6}
    assert verify(school,result['entries'])==[]


def test_friday_target_is_a_preference_not_a_hard_constraint():
    school=School(days=5,periods=3,preferred_friday_hours=2,max_daily_hours=1,teachers=[{'name':'A'}],lessons=[dict(classroom='C',subject='X',teacher='A',hours=5)])
    result=generate(school)
    assert result['verified'] and result['friday_loads']=={'C':1}
    assert result['friday_deviation']==1
    assert verify(school,result['entries'])==[]
