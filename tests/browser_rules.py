"""Run with the server started; uses a fresh isolated browser context."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(os.environ.get('ORARI_TEST_URL','http://127.0.0.1:8000/'))
    page.get_by_label('Ditë mësimi në javë').select_option('2')
    page.get_by_label('Orë mësimi në ditë',exact=True).fill('4')
    page.get_by_label('Minimum orë / ditë',exact=True).fill('2')
    page.get_by_label('Maksimum orë / ditë',exact=True).fill('2')
    page.get_by_label('Maksimum i një lënde / ditë',exact=True).fill('1')
    page.get_by_role('button',name='Ruaj javën',exact=True).click()
    page.get_by_role('button',name='♙ Profesorët').click()
    page.get_by_role('button',name='+ Shto profesor').click()
    page.get_by_label('Emri dhe mbiemri').fill('Arta')
    page.get_by_role('button',name='Ruaj profesorin').click()
    page.get_by_role('button',name='▤ Klasat & lëndët').click()
    page.get_by_label('Emri i klasës',exact=True).fill('VI-1')
    page.get_by_role('button',name='Shto klasë',exact=True).click()
    page.get_by_role('button',name='Rregullat',exact=True).click()
    page.get_by_label('Minimum orë / ditë për klasën').fill('2')
    page.get_by_label('Maksimum orë / ditë për klasën').fill('2')
    page.get_by_role('button',name='Ruaj rregullat').click()
    page.get_by_label('Emri i lëndës',exact=True).fill('Matematikë')
    page.get_by_role('button',name='Shto lëndë',exact=True).click()
    page.get_by_role('button',name='≡ Ngarkesa mësimore').click()
    page.get_by_label('Klasa',exact=True).select_option('VI-1')
    page.get_by_label('Lënda',exact=True).select_option('Matematikë')
    page.get_by_label('Profesori',exact=True).select_option('Arta')
    page.get_by_label('Orë / javë',exact=True).fill('4')
    page.get_by_label('Maksimum i kësaj lënde / ditë',exact=True).fill('2')
    page.get_by_label('Blloqe dyshe të kërkuara / javë',exact=True).fill('2')
    page.get_by_role('button',name='+ Shto angazhimin').click()
    page.get_by_role('button',name='▥ Orari javor').click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('✓ Orar i verifikuar',exact=False).wait_for(timeout=20000)
    assert page.evaluate('result.entries.map(e=>e.slot).sort((a,b)=>a-b)')==[0,1,4,5]
    page.get_by_role('button',name='≡ Ngarkesa mësimore').click()
    page.locator('#lesson-list').get_by_role('button',name='Ndrysho',exact=True).click()
    assert page.get_by_label('Blloqe dyshe të kërkuara / javë',exact=True).input_value()=='2'
    page.get_by_label('Maksimum i kësaj lënde / ditë',exact=True).fill('1')
    page.get_by_role('button',name='Ruaj ndryshimin').click()
    page.get_by_role('button',name='▥ Orari javor').click()
    page.get_by_role('button',name='Gjenero orarin →').click()
    page.get_by_text('blloqet dyshe kërkojnë kufi ditor së paku 2.',exact=False).wait_for(timeout=20000)
    page.reload()
    assert page.evaluate('state.minDaily')==2
    assert page.evaluate('state.classRules[0].max_daily_hours')==2
    assert page.evaluate('state.lessons[0].double_periods')==2
    assert not errors,errors
    print('PASS: daily school/class rules, subject override, disjoint double periods, conflict explanation, edit and persistence')
    browser.close()
