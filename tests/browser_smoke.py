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
    page.get_by_label('Maksimumi i orëve në javë',exact=True).fill('4')
    for day in ['Martë','Enjte','Premte']:
        page.locator('#working-days').get_by_label(day,exact=True).uncheck()
    page.get_by_label('Nga ora mësimore',exact=True).select_option('3')
    page.get_by_label('Deri në orën mësimore',exact=True).select_option('4')
    page.get_by_role('button',name='Zbato në kalendar',exact=True).click()
    assert page.get_by_role('button',name='Martë, ora 3: i bllokuar',exact=True).is_visible()
    assert page.get_by_role('button',name='Hënë, ora 3: i disponueshëm',exact=True).is_visible()
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
    # A late-only teacher cannot leave the class waiting for its first two periods.
    page.get_by_text('Nuk ekziston orar me këto kufizime.',exact=False).wait_for(timeout=20000)
    page.get_by_role('button',name='♙ Profesorët').click()
    page.get_by_role('button',name='+ Shto profesor').click()
    page.get_by_label('Emri dhe mbiemri').fill('Profesor i mëngjesit')
    page.get_by_role('button',name='Ruaj profesorin').click()
    page.get_by_role('button',name='▤ Klasat & lëndët').click()
    page.get_by_label('Emri i lëndës',exact=True).fill('Gjuhë')
    page.get_by_role('button',name='Shto lëndë',exact=True).click()
    page.get_by_role('button',name='≡ Ngarkesa mësimore').click()
    page.get_by_label('Klasa',exact=True).select_option('VI-1')
    page.get_by_label('Lënda',exact=True).select_option('Gjuhë')
    page.get_by_label('Profesori',exact=True).select_option('Profesor i mëngjesit')
    page.get_by_label('Orë / javë',exact=True).fill('4')
    page.get_by_role('button',name='+ Shto angazhimin').click()
    page.get_by_role('button',name='▥ Orari javor').click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('✓ Orar i verifikuar',exact=False).wait_for(timeout=20000)
    assert page.locator('.lesson-block').count()==8
    assert page.evaluate("result.entries.filter(e=>snapshot.lessons[e.lesson].teacher==='Test Profesor').every(e=>[0,2].includes(Math.floor(e.slot/6))&&[2,3].includes(e.slot%6))")
    page.get_by_role('button',name='Sipas profesorit',exact=True).click()
    assert page.locator('.lesson-block').count()==4
    page.get_by_role('button',name='↓ CSV',exact=True).is_enabled()
    page.get_by_role('button',name='♙ Profesorët').click()
    page.get_by_role('button',name='Disponueshmëria / Ndrysho').first.click()
    assert page.get_by_label('Maksimumi i orëve në javë',exact=True).input_value()=='4'
    page.get_by_label('Maksimumi i orëve në javë',exact=True).fill('3')
    page.get_by_role('button',name='Ruaj profesorin').click()
    page.get_by_role('button',name='▥ Orari javor').click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('maksimumi javor është 3',exact=False).wait_for(timeout=20000)
    page.reload()
    assert page.evaluate('JSON.parse(localStorage.getItem("orari-v2")).lessons.length')==2
    page.get_by_role('button',name='↻ Shembull i vogël',exact=True).click()
    page.get_by_role('button',name='Anulo',exact=True).click()
    assert page.evaluate('JSON.parse(localStorage.getItem("orari-v2")).teachers[0].name')=='Test Profesor'
    page.get_by_role('button',name='↻ Shembull i vogël',exact=True).click()
    page.get_by_role('button',name='Vazhdo',exact=True).click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('✓ Orar i verifikuar',exact=False).wait_for(timeout=20000)
    assert page.locator('.lesson-block').count()==11
    # The full-school view is a projection of the same verified timetable.
    page.get_by_role('button',name='Të gjitha klasat',exact=True).click()
    assert page.locator('.all-day').count()==5
    assert page.locator('.all-classes-table tbody tr').count()==30
    assert page.locator('.all-classes-table td strong').count()==22
    assert not page.locator('#view-select').is_visible()
    expected=page.evaluate("result.entries.map(e=>({slot:String(e.slot),classroom:snapshot.lessons[e.lesson].classroom,text:snapshot.lessons[e.lesson].teacher}))")
    actual=page.locator('.all-classes-table td[data-slot]').evaluate_all("cells=>cells.map(c=>({slot:c.dataset.slot,classroom:c.dataset.classroom,text:c.querySelector('strong').textContent}))")
    key=lambda e:(e['slot'],e['classroom'])
    assert sorted(actual,key=key)==sorted(expected,key=key)
    page.get_by_label('Përmbajtja e qelizës',exact=True).select_option('both')
    assert page.locator('.all-classes-table td small').count()==22
    page.get_by_label('Përmbajtja e qelizës',exact=True).select_option('subject')
    assert page.locator('.all-classes-table td strong').filter(has_text='Matematikë').count()==8
    page.get_by_label('Përmbajtja e qelizës',exact=True).select_option('teacher')
    page.screenshot(path='/tmp/orari-all-classes.png',full_page=True)
    page.emulate_media(media='print')
    assert page.locator('.all-day').first.is_visible()
    assert not page.locator('.sidebar').is_visible()
    assert page.evaluate("getComputedStyle(document.querySelector('#schedule')).overflowX")=='visible'
    page.pdf(path='/tmp/orari-all-classes.pdf',format='A4',print_background=True)
    page.emulate_media(media='screen')
    page.get_by_role('button',name='Sipas sallës',exact=True).click()
    assert page.locator('.lesson-block').count()==4
    page.get_by_role('button',name='Sipas klasës',exact=True).click()
    assert page.locator('.lesson-block').count()==11
    # Classes without assigned hours must also appear as empty columns.
    page.get_by_role('button',name='▤ Klasat & lëndët').click()
    page.get_by_label('Emri i klasës',exact=True).fill('VII-1')
    page.get_by_role('button',name='Shto klasë',exact=True).click()
    page.get_by_role('button',name='▥ Orari javor').click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('✓ Orar i verifikuar',exact=False).wait_for(timeout=20000)
    page.get_by_role('button',name='Të gjitha klasat',exact=True).click()
    assert page.locator('.all-classes-table thead th').count()==20
    assert page.locator('.all-classes-table td strong').count()==22
    assert page.locator('.all-classes-table tbody tr td:last-child .all-free').count()==30
    page.screenshot(path='/tmp/orari-desktop.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.get_by_role('button',name='Të gjitha klasat',exact=True).click()
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
    # Load the photographed school and download all three native formats.
    page.set_viewport_size({'width':1440,'height':1100})
    page.get_by_role('button',name='▥ Shembulli nga fotoja',exact=True).click()
    page.get_by_role('button',name='Vazhdo',exact=True).click()
    page.get_by_text('Transkriptimi nga fotoja u kontrollua',exact=False).wait_for(timeout=20000)
    assert page.locator('.all-classes-table td strong').count()==199
    assert page.locator('.all-classes-table thead th').count()==35
    assert page.locator('.all-classes-table').first.evaluate('(e)=>e.getBoundingClientRect().width') < 1200
    assert page.locator('.all-classes-table').first.locator('thead th').last.evaluate('(e)=>e.getBoundingClientRect().right') <= page.locator('#schedule').evaluate('(e)=>e.getBoundingClientRect().right')+1
    assert page.locator('.all-classes-table').first.locator('tbody tr').first.locator('td').first.inner_text()=='Meritë'
    assert page.locator('.all-classes-table').first.locator('tbody tr').first.locator('td').last.inner_text()=='Nazim'
    for format,label in [('xlsx','Excel'),('docx','Word'),('pdf','PDF')]:
        with page.expect_download() as download_event:
            page.get_by_role('button',name=label,exact=True).click()
        downloaded=download_event.value
        assert downloaded.suggested_filename=='orari-javor.'+format
        downloaded.save_as('/tmp/orari-photo.'+format)
    page.screenshot(path='/tmp/orari-photo-example.png',full_page=True)
    # Change a real teacher's requirements and regenerate the same 199-hour demand.
    page.get_by_role('button',name='♙ Profesorët').click()
    page.get_by_role('searchbox',name='Kërko profesorin').fill('Agnesa')
    page.get_by_role('button',name='Disponueshmëria / Ndrysho').click()
    page.get_by_label('Maksimumi i orëve në javë',exact=True).fill('4')
    for day in ['Hënë','Mërkurë','Enjte']:
        page.locator('#working-days').get_by_label(day,exact=True).uncheck()
    page.get_by_label('Nga ora mësimore',exact=True).select_option('3')
    page.get_by_role('button',name='Zbato në kalendar',exact=True).click()
    page.get_by_role('button',name='Ruaj profesorin').click()
    assert page.locator('#xlsx').is_disabled()
    page.get_by_role('button',name='▥ Orari javor').click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('✓ Orar i verifikuar',exact=False).wait_for(timeout=30000)
    assert page.locator('.all-classes-table td strong').count()==199
    assert page.evaluate("result.entries.filter(e=>snapshot.lessons[e.lesson].teacher==='Agnesa').length") == 4
    assert page.evaluate("result.entries.filter(e=>snapshot.lessons[e.lesson].teacher==='Agnesa').every(e=>[1,4].includes(Math.floor(e.slot/7))&&e.slot%7>=2)")
    assert not errors, errors
    print('PASS: teacher/calendar CRUD, class/subject forms, assignment, generation, views, persistence, replace confirmation, mobile layout, v1 migration; no browser errors')
    browser.close()
