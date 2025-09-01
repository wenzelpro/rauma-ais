# BarentsWatch AIS – Ships in Area (Heroku-ready)

Et lite Flask-API som returnerer skip i et område definert av `map.geojson`, ved å bruke BarentsWatch AIS.

## Endepunkt
- `GET /health` – enkel helsesjekk
- `GET /ships` – leser geojson fra `map.geojson` (kan overstyres med `GEOJSON_PATH`)
- `POST /ships` – send en GeoJSON `geometry` (Polygon/MultiPolygon) i request-body
- `GET /data` – viser innholdet i tabellen `seen_mmsi`
- `DELETE /data` – tømmer tabellen `seen_mmsi` og tilhørende cache

## Kjør lokalt
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# (valgfritt) rediger .env
python app.py
```

## Deploy til Heroku
```bash
heroku create
heroku buildpacks:set heroku/python
heroku config:set BW_CLIENT_ID="<your_client_id>" \
                   BW_CLIENT_SECRET="<your_client_secret>"
# valgfritt kortlivet token:
# heroku config:set BW_ACCESS_TOKEN="..."

git init
git add .
git commit -m "Initial"
git branch -M main
heroku git:remote -a $(heroku apps:info -s | grep web_url | cut -d= -f2 | sed 's#https://##; s#/.##')
git push heroku main
heroku open
```

## Sikkerhet
Ikke sjekk inn `.env`/hemmeligheter i git. I Heroku settes hemmeligheter med `heroku config:set`. Client Credentials anbefales over statiske tokens (tokens utløper typisk etter 1 time).

## Miljøvariabler
Kopier `.env.example` til `.env` og fyll inn de nødvendige variablene:

- `BW_CLIENT_ID`, `BW_CLIENT_SECRET` – **påkrevd** OAuth2 Client Credentials
- `BW_ACCESS_TOKEN` – valgfritt; bypasser client credentials (kortlivet)
- `GEOJSON_PATH` – valgfritt; sti til standard GeoJSON (default `map.geojson`)
- `MAX_AREA_KM2` – valgfritt; maks areal i km² (default 500)
- `SLACK_WEBHOOK_URL` – valgfritt; Slack Incoming Webhook for varsling ved nye skip
- `DATABASE_URL` – valgfritt; URL til Postgres/SQLite for lagring av sett av kjente MMSI

### Database for vedvarende "sett"-liste
For at appen skal huske hvilke skip som allerede er varslet mellom kjøringer (f.eks. ved bruk av Heroku Scheduler) må
`DATABASE_URL` peke til en vedvarende database.

#### Heroku Postgres
```bash
heroku addons:create heroku-postgresql:mini
# DATABASE_URL settes automatisk av Heroku
```

#### Lokal SQLite (kun utvikling)
```bash
export DATABASE_URL=sqlite:///seen.db
```

Uten en database vil alle skip varsles på nytt hver gang polleren kjører.
### Periodisk polling
For å få varsler uten å gjøre HTTP-kall selv kan du sette opp [Heroku Scheduler](https://elements.heroku.com/addons/scheduler) til å kjøre
`python poller.py` hvert par minutter. Scheduler-dyno deler `DATABASE_URL` med web-dyno, så nye skip varsles kun én gang.
For å tømme listen over kjente skip kan du kjøre `python poller.py --clear`.
