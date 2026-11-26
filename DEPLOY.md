# Deploying Crown Barbers

Everything runs in the Google Cloud project `crown-barbers-71641` (the same project as Firebase), region `europe-west2` (London). Commands are run from the project folder with the virtual environment active.

## One-off setup

1. Google Cloud console: link billing (free trial) and set a budget alert.
2. Install the gcloud CLI and log in:
   ```bash
   curl https://sdk.cloud.google.com | bash
   gcloud init
   ```
3. Turn on the services used:
   ```bash
   gcloud services enable appengine.googleapis.com cloudbuild.googleapis.com cloudfunctions.googleapis.com run.googleapis.com artifactregistry.googleapis.com cloudscheduler.googleapis.com
   ```
4. MongoDB Atlas: Network Access allows `0.0.0.0/0` (App Engine has no fixed address; the database password still protects it).
5. Firebase: add the live domain under Authentication > Settings > Authorized domains.
6. Brevo: verified sender, and an API key with Transactional email permission.
7. Create the App Engine app (once; the region can't change):
   ```bash
   gcloud app create --region=europe-west2
   ```

## Secrets

Secrets are kept in `.env` on the developer's machine. This script turns them into the three settings files Google needs. All three are git-ignored.

```bash
python make_secrets.py
```

| File | Used by |
| --- | --- |
| `secrets.yaml` | the Flask app on App Engine (with a fresh production `SECRET_KEY`) |
| `functions/booking-email.env.yaml` | the booking-email function |
| `functions/send-reminders.env.yaml` | the send-reminders function |

Run it again after any change to `.env`, then redeploy whatever uses the changed value.

## Deploy the web app

```bash
python -m pytest
python make_secrets.py
gcloud app deploy
```

`app.yaml` runs gunicorn on Python 3.12 with one F1 instance at most, UK time, and HTTPS only. `.gcloudignore` keeps tests, secrets and the functions out of the upload.

## Deploy the cloud functions

```bash
gcloud functions deploy booking-email --gen2 --runtime=python312 --region=europe-west2 --source=functions/booking_email --entry-point=send_booking_email --trigger-http --allow-unauthenticated --env-vars-file=functions/booking-email.env.yaml

gcloud functions deploy send-reminders --gen2 --runtime=python312 --region=europe-west2 --source=functions/send_reminders --entry-point=send_reminders --trigger-http --allow-unauthenticated --timeout=120 --env-vars-file=functions/send-reminders.env.yaml
```

The first deploy of `booking-email` prints its URL, which goes into `.env` as `EMAIL_FUNCTION_URL`. Then run `make_secrets.py` again and deploy `send-reminders` and the app.

## Schedule the reminders

```bash
REMINDERS_URL=$(gcloud functions describe send-reminders --gen2 --region=europe-west2 --format='value(serviceConfig.uri)')
SECRET=$(python -c "from dotenv import dotenv_values; print(dotenv_values('.env')['FUNCTION_SECRET'])")
gcloud scheduler jobs create http send-reminders-daily --location=europe-west2 --schedule="0 18 * * *" --time-zone="Europe/London" --uri="$REMINDERS_URL" --http-method=POST --headers="X-Function-Secret=$SECRET" --attempt-deadline=180s
```

## Database changes

```bash
python -m flask --app run init-db      # create tables (first time)
python -m flask --app run upgrade-db   # cancelled bookings free their slot (run once)
python seed.py                          # starter services and opening hours
```

## Checking it works

```bash
gcloud app browse
gcloud app logs tail -s default
gcloud functions logs read booking-email --gen2 --region=europe-west2 --limit=20
gcloud scheduler jobs run send-reminders-daily --location=europe-west2
```

## Cost controls

- App Engine: at most one F1 instance, scales to zero when idle
- Cloud Run functions and Cloud Scheduler: within the free tier
- Budget alert on the billing account
