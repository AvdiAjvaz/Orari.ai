# Orari.ai

Mini aplikacion për gjenerimin e orareve shkollore: FastAPI + OR-Tools CP-SAT, ndërfaqe në shqip, ruajtje lokale në shfletues dhe eksport CSV.

## Zhvillimi

```sh
cd /workspace/Orari.ai
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Hap aplikacionin përmes portit 8000 në mjedisin e zhvillimit. Ngarko shembullin dhe shtyp “Gjenero orarin”. Dokumentimi API: `/docs`; kontrolli i shëndetit: `/api/health`.

```sh
.venv/bin/python -m pytest -q
```

Shih [arkitekturën](docs/ARCHITECTURE.md) për kufijtë, modelin dhe hapat vijues. Nuk kërkohen kredenciale ose shërbime të jashtme. Mos e ekspozo publikisht pa autentikim dhe kufizim të kërkesave.

## Ndërfaqja V2

- Profesorë: formular për emrin, maksimum javor (p.sh. 20/22), ditë pune dhe interval orësh (p.sh. nga ora e tretë), plus kalendar me klikim për përjashtime. Kufijtë janë striktë.
- Klasa dhe lëndë: lista të veçanta, ndryshim emrash dhe mbrojtje nga fshirja e elementeve që përdoren.
- Ngarkesa: zgjedhje nga menyja, ndryshim/fshirje dhe përmbledhje e orëve për klasë.
- Orari: pamje sipas klasës, profesorit ose sallës, printim dhe eksport CSV.
- “Të gjitha klasat”: tabela sipas ditës, klasat në kolona dhe orët në rreshta; zgjedhje për emrin e profesorit, lëndën ose të dyja. Përfshihen edhe klasat pa ngarkesë. Printimi / ruajtja si PDF ndjek pamjen e zgjedhur.
- Të dhënat e versionit të parë barten automatikisht; ruhen vetëm në shfletuesin aktual.

Kontrolli i ndërfaqes me shfletues (opsional për zhvillim, kërkon Chromium dhe `pip install playwright`):

```sh
python tests/browser_smoke.py
```

Nise serverin më parë. `ORARI_TEST_URL` mund të përcaktojë adresën e testimit. Testi përdor një sesion të izoluar shfletuesi.

## Shembulli nga fotoja dhe eksportet

Butoni **Shembulli nga fotoja** ngarkon 6 klasat (10/8, 11/9, 12/9, 10/7, 11/8, 12/8), 5 ditë, 7 orë/ditë dhe 199 orët e transkriptuara. Fillimisht shfaqet orari burimor i kontrolluar; pas ndryshimit të një profesori ose angazhimi, shtyp **Gjenero orarin**. Gjenerimi ruan numrin e orëve për çdo angazhim, por mund t'i zhvendosë të gjitha orët; nuk bëhet ende optimizim për ndryshime minimale.

Fotoja nuk tregon lëndët për shumicën e profesorëve, ndaj përdoret **Lëndë e papërcaktuar**. Për **Sociologji** nuk shfaqet profesori: vendmbajtësit **Pa caktuar · klasa** duhen zëvendësuar me emrin real. Disponueshmëria dhe kufijtë javorë nuk inferohen nga fotoja. Shembulli i vogël mbetet i disponueshëm. Të dy butonat kërkojnë konfirmim para zëvendësimit të të dhënave aktuale.

Butonat **Excel**, **Word** dhe **PDF** shkarkojnë skedarë të vërtetë `.xlsx`, `.docx` dhe `.pdf`, sipas pamjes aktuale (të gjitha klasat ose klasa/profesori/salla e zgjedhur). Eksporti e kontrollon përsëri orarin në server dhe refuzon rezultate të pavlefshme. PDF përfshin fontet shqip; Excel ka nga një fletë për ditë në pamjen e përbashkët. CSV dhe printimi ekzistues mbeten.


## Fillimi në orën e parë dhe pa orë të zbrazëta

Çdo klasë që ka mësim në një ditë nis detyrimisht në orën e parë dhe vazhdon pa boshllëqe deri në orën e fundit të planifikuar. Orët pas përfundimit të mësimit mbeten të lira; një ditë mund të mbetet pa mësim nëse ngarkesa nuk kërkon ndryshe. Ky është kusht strikt i solver-it, verifikuesit dhe eksporteve. Një profesor mund të fillojë nga ora e tretë, por dy orët e para të klasës duhet të mbulohen nga profesorë të tjerë. Nuk ndryshohen pushimet e zakonshme mes orëve: ndalohen vetëm terminet mësimore të zbrazëta.


## Kufijtë ditorë, lëndët dhe orët dyshe

- **Përmbledhja → Java shkollore:** minimumi/maksimumi i orëve për klasat në çdo ditë dhe kufiri ditor i një lënde. Fushat bosh përdorin ditën e plotë / pa kufi shtesë. Minimumi 0 lejon ditë pa mësim.
- **Klasat & lëndët → Rregullat** pranë klasës: kufij ditorë të veçantë. Bosh trashëgon kufirin e shkollës; 0 lejon ditë të lira për atë klasë.
- **Ngarkesa mësimore:** maksimumi ditor i lëndës për klasën dhe numri i blloqeve dyshe të kërkuara. Për 4 orë/javë, 2 blloqe kërkojnë dy çifte të ndara pa mbivendosje; kufiri 2/ditë i shpërndan në ditë të ndryshme. Mund të ketë edhe 3 orë me 1 bllok + 1 orë të vetme.

Kufiri i lëndës numërohet bashkë për të gjithë profesorët e saj në të njëjtën klasë. Kufiri specifik zëvendëson atë të shkollës; kur ka disa kufij specifikë për të njëjtën klasë/lëndë, merret më i ulëti. Për orë dyshe duhet të lejohet së paku 2 orë lënde/ditë. Blloqet nuk kalojnë nga një ditë në tjetrën. Mungesa e të dhënave të lëndëve në foto nuk trajtohet si një lëndë reale e përbashkët për kufirin global.

Kontrolli i formularëve të këtyre rregullave: `python tests/browser_rules.py` (me serverin të nisur dhe Playwright/Chromium si te kontrolli i ndërfaqes).
