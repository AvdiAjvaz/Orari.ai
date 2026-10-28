import json,os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1100})
    page=context.new_page()
    errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
    state=dict(days=3,periods=2,teachers=[dict(name=n,blocked=[]) for n in ['A','B','C']],classes=['C','D'],subjects=['Math','Science','Other'],lessons=[dict(classroom='C',subject='Math',teacher='A',hours=2,room=''),dict(classroom='C',subject='Science',teacher='B',hours=2,room=''),dict(classroom='D',subject='Other',teacher='C',hours=1,room=''),dict(classroom='D',subject='Math',teacher='A',hours=1,room='')])
    page.add_init_script('localStorage.setItem("orari-v2",'+json.dumps(json.dumps(state))+')')
    base=os.environ.get('ORARI_TEST_URL','http://127.0.0.1:8000/')
    page.goto(base)
    # Inject an independently validated deterministic starting timetable.
    entries=[dict(lesson=0,slot=0),dict(lesson=1,slot=1),dict(lesson=1,slot=2),dict(lesson=0,slot=3),dict(lesson=2,slot=0),dict(lesson=3,slot=1)]
    page.evaluate("""async entries=>{snapshot=payload();const r=await fetch('/api/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({school:snapshot,entries})});result=await r.json();mode='classroom';cachePlan();} """,entries)
    # The initialization script is removed for subsequent reloads by using a new page.
    context=page.context;page.close();page=context.new_page();page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(base+'#schedule')
    page.get_by_text('Orari i ruajtur u rikontrollua',exact=False).wait_for(timeout=15000)
    source=page.locator('.lesson-block[data-lesson="0"][data-entry-slot="0"]')
    source.drag_to(page.locator('.schedule-cell[data-slot="2"]'))
    page.get_by_text('Dy orët u ndërruan dhe u verifikuan.',exact=True).wait_for()
    assert page.evaluate('result.entries.some(e=>e.lesson===0&&e.slot===2)')
    page.get_by_role('button',name='↶ Kthe lëvizjen',exact=True).click()
    page.get_by_text('Lëvizja e fundit u kthye.',exact=True).wait_for()
    assert page.evaluate('result.entries.some(e=>e.lesson===0&&e.slot===0)')
    page.locator('.lesson-block[data-lesson="0"][data-entry-slot="0"]').drag_to(page.locator('.schedule-cell[data-slot="1"]'))
    page.locator('#notice').filter(has_text='Përplasje: A').wait_for()
    assert page.evaluate('result.entries.some(e=>e.lesson===0&&e.slot===0)')
    # Two-tap movement to an empty slot works on a phone and preserves the no-gap rule.
    page.set_viewport_size({'width':390,'height':844})
    page.locator('.lesson-block[data-lesson="0"][data-entry-slot="3"]').click()
    page.locator('.schedule-cell[data-slot="4"]').click()
    page.get_by_text('Ora u zhvendos dhe u verifikua.',exact=True).wait_for()
    assert page.evaluate('result.entries.some(e=>e.lesson===0&&e.slot===4)')
    page.reload();page.get_by_text('Orari i ruajtur u rikontrollua',exact=False).wait_for()
    assert page.evaluate('result.entries.some(e=>e.lesson===0&&e.slot===4)')
    page.set_viewport_size({'width':1440,'height':1100})
    page.get_by_role('button',name='🔒 Orë statike',exact=True).click()
    page.get_by_label('Klasa · Lënda · Profesori',exact=True).select_option('0')
    page.get_by_role('button',name='Fikso Hënë, ora 1',exact=True).click()
    page.get_by_role('button',name='Ruaj orët statike',exact=True).click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('✓ Orar i verifikuar',exact=False).wait_for(timeout=20000)
    locked=page.locator('.lesson-block[data-lesson="0"][data-entry-slot="0"]')
    assert locked.get_attribute('draggable')=='false'
    assert locked.locator('.fixed-marker').count()==1
    locked.click();page.locator('#notice').filter(has_text='Kjo orë është statike').wait_for()
    # Real requested case: Friday period 6 for the photo's 12/9 Sociology assignment.
    page.get_by_role('button',name='▥ Shembulli nga fotoja',exact=True).click()
    page.get_by_role('button',name='Vazhdo',exact=True).click()
    page.get_by_text('Transkriptimi nga fotoja u kontrollua',exact=False).wait_for()
    index=page.evaluate("state.lessons.findIndex(l=>l.classroom==='12/9'&&l.subject==='Sociologji')")
    page.get_by_role('button',name='🔒 Orë statike',exact=True).click()
    page.get_by_label('Klasa · Lënda · Profesori',exact=True).select_option(str(index))
    page.get_by_role('button',name='Fikso Premte, ora 6',exact=True).click()
    page.get_by_role('button',name='Ruaj orët statike',exact=True).click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('✓ Orar i verifikuar',exact=False).wait_for(timeout=30000)
    assert page.evaluate('(index)=>result.entries.some(e=>e.lesson===index&&e.slot===33)',index)
    assert page.locator('.all-classes-table td[data-classroom="12/9"][data-slot="33"] .fixed-marker').count()==1
    page.screenshot(path='/tmp/orari-fixed-example.png',full_page=True)
    assert not errors,errors
    print('PASS: drag swap, rejection without mutation, undo, phone two-tap move, reload persistence, fixed lock, Friday 6 Sociology, regeneration')
    browser.close()
