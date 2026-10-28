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
