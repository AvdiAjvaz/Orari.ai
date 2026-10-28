from playwright.sync_api import sync_playwright
import os

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100})
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(os.environ.get('ORARI_TEST_URL', 'http://127.0.0.1:8000/'))
    page.get_by_role('button',name='♙ Profesorët').click()
    page.get_by_role('button',name='+ Shto profesor').click()
    page.get_by_label('Emri dhe mbiemri').fill('Test Profesor')
    page.get_by_role('button',name='Hënë, ora 1: i disponueshëm',exact=True).click()
    assert page.get_by_role('button',name='Hënë, ora 1: i bllokuar',exact=True).get_attribute('aria-pressed')=='true'
    page.get_by_role('button',name='Ruaj profesorin').click()
    assert page.locator('.teacher-card').count()==1
    page.get_by_role('button',name='▤ Klasat & lëndët').click()
    page.get_by_label('Emri i klasës',exact=True).fill('VI-1')
    page.get_by_role('button',name='Shto klasë',exact=True).click()
    page.get_by_label('Emri i lëndës',exact=True).fill('Matematikë')
    page.get_by_role('button',name='Shto lëndë',exact=True).click()
    page.get_by_role('button',name='≡ Ngarkesa mësimore').click()
    page.get_by_label('Klasa',exact=True).select_option('VI-1')
    page.get_by_label('Lënda',exact=True).select_option('Matematikë')
    page.get_by_label('Profesori',exact=True).select_option('Test Profesor')
    page.get_by_label('Orë / javë',exact=True).fill('4')
    page.get_by_role('button',name='+ Shto angazhimin').click()
    assert page.locator('#lesson-list tr').count()==1
    page.get_by_role('button',name='▥ Orari javor').click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('✓ Orar i verifikuar',exact=False).wait_for(timeout=20000)
    assert page.locator('.lesson-block').count()==4
    page.get_by_role('button',name='Sipas profesorit',exact=True).click()
    assert page.locator('.lesson-block').count()==4
    page.get_by_role('button',name='↓ CSV',exact=True).is_enabled()
    page.reload()
    assert page.evaluate('JSON.parse(localStorage.getItem("orari-v2")).lessons.length')==1
    page.get_by_role('button',name='↻ Provo me shembull',exact=True).click()
    page.get_by_role('button',name='Anulo',exact=True).click()
    assert page.evaluate('JSON.parse(localStorage.getItem("orari-v2")).teachers[0].name')=='Test Profesor'
    page.get_by_role('button',name='↻ Provo me shembull',exact=True).click()
    page.get_by_role('button',name='Vazhdo',exact=True).click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('✓ Orar i verifikuar',exact=False).wait_for(timeout=20000)
    assert page.locator('.lesson-block').count()==11
    page.screenshot(path='/tmp/orari-desktop.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path='/tmp/orari-mobile.png',full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile overflow'
    page.get_by_role('button',name='♙ Profesorët').click()
    page.get_by_role('button',name='Disponueshmëria / Ndrysho').first.click()
    assert page.get_by_label('Emri dhe mbiemri').input_value()=='Arta Krasniqi'
    page.get_by_role('button',name='Anulo',exact=True).click()
    # Existing v1 data migrates without discarding teacher availability.
    page.evaluate('localStorage.clear()')
    page.evaluate('''localStorage.setItem('orari-v1',JSON.stringify({days:'5',periods:'6',teachers:'Arta | 1:1, 5:6',lessons:[{classroom:'C',subject:'Math',teacher:'Arta',hours:2,room:''}]}))''')
    page.reload()
    saved=page.evaluate('JSON.parse(localStorage.getItem("orari-v2"))')
    assert saved['teachers'][0]['blocked']==['0:0','4:5']
    assert saved['classes']==['C'] and len(saved['lessons'])==1
    assert not errors, errors
    print('PASS: teacher/calendar CRUD, class/subject forms, assignment, generation, views, persistence, replace confirmation, mobile layout, v1 migration; no browser errors')
    browser.close()
