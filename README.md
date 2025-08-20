# BarentsWatch AIS – Ships in Area (Heroku-ready)

Et lite Flask-API som returnerer skip i et område definert av `map.geojson`, ved å bruke BarentsWatch AIS.

## Endepunkt
- `GET /health` – enkel helsesjekk
- `GET /ships` – leser geojson fra `map.geojson` (kan overstyres med `GEOJSON_PATH`)
- `POST /ships` – send en GeoJSON `geometry` (Polygon/MultiPolygon) i request-body

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
heroku config:set BW_CLIENT_ID="wenzel.prokosch%40andalsnes-avis.no%3ARauma%20AIS" \
                   BW_CLIENT_SECRET="myxdag-gafjoq-Purze0"
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
