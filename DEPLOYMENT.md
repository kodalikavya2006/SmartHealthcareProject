# Public deployment

## Vercel

The root `app.py` exports the Flask application for Vercel's Python runtime, and `public/` contains the static frontend assets. Import the GitHub repository into Vercel and deploy it with the root directory set to the repository root. Vercel assigns the public URL after the deployment succeeds.

## Render

CareNest can also be deployed as a Render Blueprint using `render.yaml`.

1. Push the project, including `render.yaml` and `requirements.txt`, to the `main` branch of the GitHub repository.
2. Sign in to [Render](https://render.com/), choose **New** > **Blueprint**, and connect `kodalikavya2006/SmartHealthcareProject`.
3. Apply the Blueprint. Render will build the Flask app and show its public URL when the service is live.

The free web service keeps a stable public URL, but may sleep when idle and take a short time to wake. This demo stores appointments and reminders in memory, so the data is lost when the server restarts or redeploys. Do not enter private health information. The local `.env` file and its Murf key are not deployed; avoid adding a paid voice API key to a publicly accessible service without appropriate usage limits and protections.
