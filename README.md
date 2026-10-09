# CareNest — Smart Healthcare Assistant

This project converts the supplied Travel Guide frontend into a healthcare assistant demo. It includes a Flask API, a chat interface, an appointment request organizer, and a medication schedule organizer.

## Features
- General health Q&A with conservative, rule-based starter responses.
- Safety response for several emergency phrases.
- Add/list/remove appointment requests.
- Add/list/remove medication reminder details.
- Responsive dashboard UI.
- Optional Murf text-to-speech playback for assistant replies.

## Run on Windows
1. Install Python 3.10 or newer.
2. Open PowerShell in the project folder.
3. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   pip install flask flask-cors
   ```
5. Start the app from the project root:
   ```powershell
   python Backend/app.py
   ```
6. Open http://127.0.0.1:5000 in your browser.

If port 5000 is already used by another app, start CareNest on port 5001 instead:
```powershell
$env:PORT = "5001"
python Backend\app.py
```
Then open http://127.0.0.1:5001. Keep that PowerShell window open while using the app, and open the URL printed by Flask rather than opening `Frontend\index.html` directly.

### Configure Murf voice generation
1. Create an API key in the [Murf API dashboard](https://murf.ai/api/dashboard).
2. Copy `.env.example` to `.env` in the project root and add the key:
   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```
   Replace the blank `MURF_API_KEY` value with your key. Keep `.env` private; it is excluded by `.gitignore`. You can optionally change `MURF_VOICE_ID`.
3. Restart the server from the project root:
   ```powershell
   python Backend\app.py
   ```
4. In chat, select **Listen** beneath an assistant reply to generate audio, then press play in the audio player. The key stays server-side; the selected reply text is sent to Murf only after the button is selected. Without a configured key, chat remains usable and the Listen action displays a setup error.

## Important implementation notes
- The assistant currently uses simple rule-based sample responses. It is not connected to MERF.ai or a medical knowledge base yet.
- Murf speech generation uses the Murf text-to-speech API and requires `MURF_API_KEY`. Generated audio uses Murf's Base64 response option; select Listen only for text you want sent to Murf.
- To connect MERF.ai, replace `assistant_reply()` in `Backend/app.py` with a server-side request to your MERF.ai workflow/API. Keep API keys in environment variables; do not put secrets in frontend JavaScript.
- Appointment requests are not sent to a real clinic and are not confirmed bookings.
- Medication reminder details are not timed notifications. Add a trusted scheduler/notification service if needed.
- Storage is in-memory for this demo and resets when the Flask server restarts. Use a properly secured database and authentication before handling real users or health information.
- The assistant is not a doctor. Do not use it for diagnosis, prescribing, or emergencies.
