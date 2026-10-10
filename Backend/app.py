import json
import os
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / 'public'


def load_local_env(env_path: Path = BASE_DIR / '.env') -> None:
    if not env_path.exists():
        return

    for line_number, line in enumerate(env_path.read_text(encoding='utf-8').splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].strip()
        key, separator, value = line.partition('=')
        key = key.strip()
        if not separator or not key or not (key[0].isalpha() or key[0] == '_') or not all(
            char.isalnum() or char == '_' for char in key
        ):
            raise RuntimeError(f'Invalid environment setting in {env_path.name} on line {line_number}.')
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not os.environ.get(key):
            os.environ[key] = value


load_local_env()

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path='')
CORS(app)

# Demo-only in-memory storage. Data resets when the server restarts.
appointments = []
reminders = []


def next_item_id(items):
    """Return the next unique integer ID for a list of stored items."""
    current_ids = [item.get('id', 0) for item in items if isinstance(item, dict)]
    return max(current_ids, default=0) + 1

SYSTEM_NOTE = (
    "You are a Smart Healthcare Assistant. Give general health information in plain language. "
    "Do not diagnose, prescribe, or recommend changing medication doses. For potentially urgent "
    "symptoms, recommend prompt professional care; for emergencies, advise local emergency services. "
    "Never claim an appointment or reminder was saved unless the relevant API confirms it."
)


def assistant_reply(message: str) -> str:
    """Safe starter responses. Replace this function with your MERF.ai/LLM API integration."""
    text = message.lower().strip()

    emergency_terms = [
        'severe chest pain', 'chest pain and difficulty breathing', 'cannot breathe',
        "can't breathe", 'difficulty breathing', 'signs of stroke', 'unconscious',
        'severe bleeding', 'overdose'
    ]
    if any(term in text for term in emergency_terms):
        return (
            "This may be a medical emergency. Please contact your local emergency number or go to "
            "the nearest emergency department now. Do not wait for an online response. If possible, "
            "ask someone nearby to help."
        )

    if any(word in text for word in ['appointment', 'book a doctor', 'schedule a doctor']):
        return (
            "I can help organize an appointment request. Use the Appointment Manager form to enter "
            "the doctor or clinic, date, and time. This demo stores a request locally in its running "
            "server; it does not contact a real clinic or confirm a medical booking."
        )

    if any(word in text for word in ['remind', 'medication reminder', 'medicine reminder', 'take my medicine']):
        return (
            "You can add a reminder in the Medication Reminders form using the schedule provided by "
            "your healthcare professional. This demo saves reminder details, but does not send timed "
            "push notifications. Do not change a prescribed dose based on this assistant."
        )

    if any(word in text for word in ['dose', 'dosage', 'which medicine', 'what medicine', 'prescribe']):
        return (
            "I can't prescribe medicine or advise you to start, stop, or change a dose. Please follow "
            "your prescription and ask a qualified doctor or pharmacist if you're unsure. If you share "
            "a general health question, I can help explain it in simple terms."
        )

    if any(word in text for word in ['blood pressure', 'bp reading']):
        return (
            "Blood pressure is recorded as two numbers: systolic pressure (when the heart beats) over "
            "diastolic pressure (between beats). One reading alone may not tell the whole story. Follow "
            "the guidance of a healthcare professional, especially if readings are repeatedly unusual or "
            "you have symptoms. I can't diagnose you from a chat."
        )

    if any(word in text for word in ['fever', 'headache', 'cough', 'pain', 'symptom', 'symptoms']):
        return (
            "I'm sorry you're not feeling well. I can share general information, but I can't diagnose "
            "the cause. Consider contacting a healthcare professional if symptoms are severe, persistent, "
            "worsening, or worrying. If you think this is an emergency, contact local emergency services."
        )

    return (
        "I can help with general health information, explain common medical terms, or help you organize "
        "appointments and medication reminders. What would you like help with? Remember, I'm an AI "
        "assistant and not a substitute for a qualified healthcare professional."
    )


def generate_murf_audio(text: str) -> dict:
    api_key = os.environ.get('MURF_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('Murf voice is not configured. Set the MURF_API_KEY environment variable and restart the server.')

    payload = {
        'text': text,
        'voiceId': os.environ.get('MURF_VOICE_ID', 'Natalie'),
        'locale': 'en-US',
        'format': 'MP3',
        'modelVersion': 'GEN2',
        'encodeAsBase64': True,
    }
    api_request = Request(
        'https://api.murf.ai/v1/speech/generate',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'api-key': api_key},
        method='POST',
    )

    try:
        with urlopen(api_request, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
    except HTTPError as error:
        try:
            error_body = json.loads(error.read().decode('utf-8'))
            if isinstance(error_body, dict):
                detail = (
                    error_body.get('message')
                    or error_body.get('error')
                    or error_body.get('detail')
                    or error_body.get('description')
                )
                if isinstance(detail, dict):
                    detail = detail.get('message') or detail.get('detail')
                if isinstance(detail, list):
                    detail = '; '.join(str(item) for item in detail)
            else:
                detail = str(error_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = None
        if error.code in (401, 403):
            raise RuntimeError('Murf rejected the API key. Check that MURF_API_KEY is valid and enabled.') from error
        if error.code == 402:
            raise RuntimeError('Murf rejected speech generation because the subscription or character allowance may be exhausted.') from error
        raise RuntimeError(detail or f'Murf speech generation failed (HTTP {error.code}).') from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError('Could not reach Murf. Check your internet connection and try again.') from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError('Murf returned an invalid response. Please try again.') from error

    if not isinstance(result, dict):
        raise RuntimeError('Murf returned an unexpected response. Please try again.')
    encoded_audio = result.get('encodedAudio')
    if encoded_audio:
        return {'audio': f"data:audio/mpeg;base64,{encoded_audio}"}
    audio_url = result.get('audioFile')
    if audio_url:
        return {'audio': audio_url}
    raise RuntimeError('Murf did not return audio. Check the selected voice and API settings.')


@app.get('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.post('/api/chat')
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get('message', '')).strip()
    if not message:
        return jsonify({'error': 'Please enter a message.'}), 400
    if len(message) > 4000:
        return jsonify({'error': 'Message is too long. Please keep it under 4000 characters.'}), 400
    return jsonify({'reply': assistant_reply(message), 'disclaimer': 'General information only; not a diagnosis or treatment plan.'})


@app.post('/api/voice')
def voice():
    data = request.get_json(silent=True) or {}
    text = str(data.get('text', '')).strip()
    if not text:
        return jsonify({'error': 'Text is required to generate speech.'}), 400
    if len(text) > 4000:
        return jsonify({'error': 'Text is too long. Please keep it under 4000 characters.'}), 400
    try:
        return jsonify(generate_murf_audio(text))
    except RuntimeError as error:
        return jsonify({'error': str(error)}), 503 if 'not configured' in str(error) else 502


@app.get('/api/appointments')
def get_appointments():
    return jsonify(appointments)


@app.post('/api/appointments')
def add_appointment():
    data = request.get_json(silent=True) or {}
    doctor = str(data.get('doctor', '')).strip()
    date = str(data.get('date', '')).strip()
    time = str(data.get('time', '')).strip()
    notes = str(data.get('notes', '')).strip()
    if not doctor or not date or not time:
        return jsonify({'error': 'Doctor/clinic, date, and time are required.'}), 400
    try:
        datetime.strptime(date, '%Y-%m-%d')
        datetime.strptime(time, '%H:%M')
    except ValueError:
        return jsonify({'error': 'Please enter a valid date and time.'}), 400
    item = {'id': next_item_id(appointments), 'doctor': doctor, 'date': date, 'time': time, 'notes': notes, 'status': 'Request saved (not booked)'}
    appointments.append(item)
    return jsonify({'message': 'Appointment request saved in this demo.', 'appointment': item}), 201


@app.delete('/api/appointments/<int:item_id>')
def delete_appointment(item_id):
    global appointments
    old_len = len(appointments)
    appointments = [item for item in appointments if item['id'] != item_id]
    if len(appointments) == old_len:
        return jsonify({'error': 'Appointment not found.'}), 404
    return jsonify({'message': 'Appointment request removed.'})


@app.get('/api/reminders')
def get_reminders():
    return jsonify(reminders)


@app.post('/api/reminders')
def add_reminder():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    schedule = str(data.get('schedule', '')).strip()
    if not name or not schedule:
        return jsonify({'error': 'Medication name and schedule are required.'}), 400
    item = {'id': next_item_id(reminders), 'name': name, 'schedule': schedule, 'note': 'Use only as prescribed; demo does not send notifications.'}
    reminders.append(item)
    return jsonify({'message': 'Reminder details saved in this demo. No timed notification was sent.', 'reminder': item}), 201


@app.delete('/api/reminders/<int:item_id>')
def delete_reminder(item_id):
    global reminders
    old_len = len(reminders)
    reminders = [item for item in reminders if item['id'] != item_id]
    if len(reminders) == old_len:
        return jsonify({'error': 'Reminder not found.'}), 404
    return jsonify({'message': 'Reminder removed.'})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '5000')), debug=True)
