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
