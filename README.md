# AIS Traffic Monitor

This project provides a small Flask web application that queries the
BarentsWatch historical AIS API for vessel traffic inside a polygon
defined in `map.geojson`. A background thread refreshes the data every
ten minutes and reports newly detected vessels to the log. Visiting the
root URL displays the current list of vessels.

## Requirements

* Python 3.11+
* `Flask`
* `gunicorn`
* `requests`
* `shapely`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Set the BarentsWatch access token in the environment:

```bash
export BW_ACCESS_TOKEN="<access token>"
```

Run the application locally:

```bash
python app.py  # development server
# or
gunicorn app:app  # production-style server
```

Then open <http://localhost:5000> to view the vessel list.

## Deployment on Heroku

1. Create the application:

   ```bash
   heroku create
   ```

2. Set the BarentsWatch access token:

   ```bash
   heroku config:set BW_ACCESS_TOKEN="<access token>"
   ```

3. Push the code to Heroku:

   ```bash
   git push heroku main
   ```

4. Open the app in a browser:

   ```bash
   heroku open
   ```

Heroku will run the app using the provided `Procfile`.
