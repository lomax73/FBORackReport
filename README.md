# Report Rack

App della famiglia FBO per documentare i collaudi di cablaggio
strutturato presso i clienti: crea un progetto, aggiungi uno o più rack,
per ogni rack uno o più elementi (patch panel o cassetti fibra, da 8 a 24
posizioni), compila le posizioni (cavo, tipo cavo, descrizione,
posizione in campo, esito test), allega i report degli strumenti di
verifica (es. export FLUKE) e genera un report PDF per il cliente.

## Sviluppo locale

```
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
venv/bin/python manage.py migrate
venv/bin/python manage.py createsuperuser
venv/bin/python manage.py runserver
```

WeasyPrint richiede Pango installato a livello di sistema:
`brew install pango` su macOS, vedi `deploy/README.md` per Linux/produzione.

Il picker cliente nel form progetto e i dati mostrati in lista/dettaglio/
PDF dipendono dall'anagrafica clienti condivisa nel Portale FBO — serve
un'istanza del Portale raggiungibile (vedi `PORTAL_INTERNAL_BASE_URL` in
`.env.example`).

## Flusso

1. Crea un progetto (nome, cliente dall'anagrafica del Portale, sito/
   cliente finale, data intervento).
2. Aggiungi uno o più rack.
3. Per ogni rack, aggiungi uno o più pannelli (patch panel o cassetto
   fibra) indicandone il numero di posizioni.
4. "Compila posizioni" per inserire cavo/descrizione/esito di ogni porta
   in un'unica pagina.
5. Carica gli allegati del rack (report degli strumenti di verifica).
6. Dalla scheda progetto, "Scarica report PDF".

## Deploy

Vedi `deploy/README.md`.
