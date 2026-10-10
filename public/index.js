const API = '/api';
const $ = (id) => document.getElementById(id);

function showTab(tab) {
  document.querySelectorAll('.tab-panel').forEach(el => el.classList.toggle('hidden', el.id !== tab));
  document.querySelectorAll('[data-tab]').forEach(el => el.classList.toggle('active', el.dataset.tab === tab));
  if (tab === 'appointments') loadAppointments();
  if (tab === 'reminders') loadReminders();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
document.querySelectorAll('[data-tab]').forEach(btn => btn.addEventListener('click', () => showTab(btn.dataset.tab)));

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options
    });
  } catch (error) {
    throw new Error('Cannot reach the CareNest server. Start Flask from the project folder and open the app at http://127.0.0.1:5000/. If port 5000 is occupied, use the alternate-port instructions in README.md.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      throw new Error('The server at this address is not serving the CareNest API. Restart CareNest and open the URL printed by Flask.');
    }
    throw new Error(data.error || 'Something went wrong. Please try again.');
  }
  return data;
}

function addMessage(text, who) {
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${who === 'user' ? 'user' : 'assistant'}`;
  bubble.textContent = text;
  $('chatMessages').appendChild(bubble);
  if (who !== 'user') {
    const controls = document.createElement('div');
    controls.className = 'flex items-center gap-3 mt-2';
    const speakButton = document.createElement('button');
    speakButton.type = 'button';
    speakButton.className = 'text-xs font-semibold text-emerald-700 hover:underline';
    speakButton.textContent = 'Listen';
    const status = document.createElement('span');
    status.className = 'text-xs text-slate-500';
    const audioPlayer = document.createElement('audio');
    audioPlayer.className = 'w-full max-w-sm mt-2';
    audioPlayer.controls = true;
    audioPlayer.hidden = true;
    speakButton.addEventListener('click', async () => {
      speakButton.disabled = true;
      speakButton.textContent = 'Generating...';
      status.textContent = '';
      try {
        const result = await api('/voice', { method: 'POST', body: JSON.stringify({ text }) });
        if (!result.audio) throw new Error('Murf returned no playable audio.');
        audioPlayer.src = result.audio;
        audioPlayer.hidden = false;
        speakButton.textContent = 'Generate again';
        status.textContent = 'Audio ready. Press play to listen.';
      } catch (error) {
        status.textContent = error.message;
        speakButton.textContent = 'Try again';
      } finally {
        speakButton.disabled = false;
      }
    });
    controls.append(speakButton, status);
    bubble.appendChild(controls);
    bubble.appendChild(audioPlayer);
  }
  $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
}
async function sendChat(message) {
  const clean = message.trim();
  if (!clean) return;
  addMessage(clean, 'user');
  $('chatInput').value = '';
  $('sendBtn').disabled = true;
  $('sendBtn').textContent = '...';
  try {
    const data = await api('/chat', { method: 'POST', body: JSON.stringify({ message: clean }) });
    addMessage(data.reply, 'assistant');
  } catch (error) {
    addMessage(`I couldn't connect to the assistant: ${error.message}`, 'assistant');
  } finally {
    $('sendBtn').disabled = false;
    $('sendBtn').textContent = 'Send';
    $('chatInput').focus();
  }
}
$('chatForm').addEventListener('submit', e => { e.preventDefault(); sendChat($('chatInput').value); });
document.querySelectorAll('.suggestion').forEach(btn => btn.addEventListener('click', () => sendChat(btn.dataset.prompt)));

function safeText(value) { return String(value ?? ''); }
function createItemCard(title, subtitle, extra, onDelete) {
  const card = document.createElement('div');
  card.className = 'rounded-2xl border border-slate-100 bg-slate-50 p-4 flex gap-3 items-start';
  const content = document.createElement('div'); content.className = 'min-w-0 flex-1';
  const heading = document.createElement('h3'); heading.className = 'font-bold break-words'; heading.textContent = title;
  const sub = document.createElement('p'); sub.className = 'text-sm text-slate-600 mt-1 break-words'; sub.textContent = subtitle;
  content.append(heading, sub);
  if (extra) { const note = document.createElement('p'); note.className = 'text-xs text-slate-400 mt-2'; note.textContent = extra; content.appendChild(note); }
  const remove = document.createElement('button'); remove.className = 'text-xs font-bold text-rose-600 hover:underline shrink-0'; remove.textContent = 'Remove'; remove.addEventListener('click', onDelete);
  card.append(content, remove); return card;
}

async function loadAppointments() {
  const list = $('appointmentsList'); list.replaceChildren();
  try {
    const items = await api('/appointments');
    if (!items.length) { list.innerHTML = '<p class="text-slate-400 text-sm">No appointment requests yet.</p>'; return; }
    items.forEach(item => list.appendChild(createItemCard(item.doctor, `${item.date} at ${item.time}`, `${item.status}${item.notes ? ' · Notes: ' + item.notes : ''}`, async () => {
      if (!confirm('Remove this appointment request?')) return;
      try { await api(`/appointments/${item.id}`, { method: 'DELETE' }); loadAppointments(); }
      catch (error) { alert(error.message); }
    })));
  } catch (error) { list.textContent = error.message; }
}
$('appointmentForm').addEventListener('submit', async e => {
  e.preventDefault(); const msg = $('apptMessage'); msg.textContent = 'Saving...'; msg.className = 'text-sm text-slate-500';
  try {
    const result = await api('/appointments', { method: 'POST', body: JSON.stringify({ doctor: $('doctor').value, date: $('apptDate').value, time: $('apptTime').value, notes: $('apptNotes').value }) });
    msg.textContent = result.message; msg.className = 'text-sm text-emerald-700'; e.target.reset(); loadAppointments();
  } catch (error) { msg.textContent = error.message; msg.className = 'text-sm text-rose-600'; }
});
$('refreshAppointments').addEventListener('click', loadAppointments);

async function loadReminders() {
  const list = $('remindersList'); list.replaceChildren();
  try {
    const items = await api('/reminders');
    if (!items.length) { list.innerHTML = '<p class="text-slate-400 text-sm">No reminder details saved yet.</p>'; return; }
    items.forEach(item => list.appendChild(createItemCard(item.name, item.schedule, item.note, async () => {
      if (!confirm('Remove these reminder details?')) return;
      try { await api(`/reminders/${item.id}`, { method: 'DELETE' }); loadReminders(); }
      catch (error) { alert(error.message); }
    })));
  } catch (error) { list.textContent = error.message; }
}
$('reminderForm').addEventListener('submit', async e => {
  e.preventDefault(); const msg = $('reminderMessage'); msg.textContent = 'Saving...'; msg.className = 'text-sm text-slate-500';
  try {
    const result = await api('/reminders', { method: 'POST', body: JSON.stringify({ name: $('medName').value, schedule: $('medSchedule').value }) });
    msg.textContent = result.message; msg.className = 'text-sm text-emerald-700'; e.target.reset(); loadReminders();
  } catch (error) { msg.textContent = error.message; msg.className = 'text-sm text-rose-600'; }
});
$('refreshReminders').addEventListener('click', loadReminders);

// Set a useful default date for appointment entry.
const today = new Date();
$('apptDate').min = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
