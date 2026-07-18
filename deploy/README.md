# Deploy sul VPS

Stesso pattern già in uso per MKRemote, il Portale, Collaudi Fibra e
FBOPreventivi (repo separato, utente di sistema dedicato, venv proprio).
Al momento nessun dominio è configurato sul VPS: si usa l'IP nudo su una
porta dedicata (vedi `nginx-rackreport-ip-provisional.conf`), da
sostituire con un sottodominio quando ci sarà un dominio reale.

**Dipendenza in più rispetto al Portale**: il PDF è generato con
WeasyPrint, che richiede librerie di sistema (non pacchetti Python) —
già installate sul VPS per Collaudi Fibra/FBOPreventivi, ma da
verificare/installare se questo è il primo deploy WeasyPrint sul server:

```
apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libcairo2
```

## Provisioning iniziale (una tantum)

```
# da root sul VPS
adduser --system --group --home /opt/rackreport rackreport
mkdir -p /opt/rackreport/app
chown rackreport:rackreport /opt/rackreport/app

apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libcairo2

sudo -u rackreport git clone https://github.com/lomax73/FBORackReport.git /opt/rackreport/app
cd /opt/rackreport/app
sudo -u rackreport python3 -m venv venv
sudo -u rackreport venv/bin/pip install -r requirements.txt

cp .env.example .env   # poi valorizzare DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, INTERNAL_API_TOKEN,
                        # PORTAL_INTERNAL_BASE_URL=https://127.0.0.1:8443, PORTAL_API_TOKEN, PORTAL_PUBLIC_URL
sudo -u rackreport venv/bin/python manage.py migrate
sudo -u rackreport venv/bin/python manage.py collectstatic --noinput
sudo -u rackreport venv/bin/python manage.py createsuperuser
mkdir -p /opt/rackreport/app/media && chown rackreport:rackreport /opt/rackreport/app/media

cp deploy/rackreport-web.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now rackreport-web.service

# Certificato self-signed (IP nudo, nessun dominio):
mkdir -p /etc/ssl/rackreport
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout /etc/ssl/rackreport/selfsigned.key \
    -out /etc/ssl/rackreport/selfsigned.crt \
    -subj "/CN=94.177.161.127"

cp deploy/nginx-rackreport-ip-provisional.conf /etc/nginx/sites-available/rackreport
ln -s /etc/nginx/sites-available/rackreport /etc/nginx/sites-enabled/rackreport
nginx -t && systemctl reload nginx
ufw allow 8446/tcp comment 'FBORackReport HTTPS'
```

Ricorda anche: `chmod 751 /opt/rackreport` (come per le altre app) perché
Nginx/www-data possa attraversare la home e servire `staticfiles/` e
`media/` (gli allegati caricati sui rack).

## API interna di gestione utenti (per il Portale)

Come per le altre app, questa app espone `accounts/` sotto
`api/internal/` per permettere al Portale FBO di creare/modificare/
eliminare utenti da remoto. **Va esposta solo in locale**, mai
pubblicamente — il location block dedicato è già incluso in
`nginx-rackreport-ip-provisional.conf`, prima di quello generico
`location /`.

1. `INTERNAL_API_TOKEN` va già valorizzato in `.env` (vedi sopra).
2. `systemctl restart rackreport-web.service` dopo aver aggiornato `.env`.
3. Configurare lo stesso token nel Portale (admin → AppLink → nuovo
   record "Report Rack", campo "API token"), insieme a
   `internal_base_url = https://127.0.0.1:8446`.

## Anagrafica clienti condivisa (dal Portale)

`Progetto.cliente_id` (UUID) si risolve in tempo reale chiamando l'API di
sola lettura del Portale (`clienti/api/internal/clienti/`), stesso
schema HTTP della gestione utenti sopra ma in direzione opposta (qui è
questa app a chiamare il Portale). Configurare in `.env`:
- `PORTAL_INTERNAL_BASE_URL` (es. `https://127.0.0.1:8443`, l'URL
  loopback del Portale, non quello pubblico)
- `PORTAL_API_TOKEN` (stesso valore di `INTERNAL_API_TOKEN` nel `.env`
  del Portale)
- `PORTAL_PUBLIC_URL` (solo per il link "Clienti (Portale)" in sidebar)

Se il Portale non risponde, il picker cliente nel form progetto mostra
un errore invece di bloccarsi, e liste/dettaglio/PDF mostrano "Cliente
non disponibile" invece di un 500.

## Deploy di un aggiornamento

```
ssh mkremote-vps
cd /opt/rackreport/app
sudo -u rackreport git pull origin main
sudo -u rackreport venv/bin/pip install -r requirements.txt
sudo -u rackreport venv/bin/python manage.py migrate
sudo -u rackreport venv/bin/python manage.py collectstatic --noinput
systemctl restart rackreport-web.service
```
