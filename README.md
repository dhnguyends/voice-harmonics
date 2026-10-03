# Voice Harmonics Analyzer (web)
# Local Web Server (self hosting)
# Prompt : https://drive.google.com/file/d/1kS82oxsR30cTwfw3ax9xZjRAoQQUsd8c/view?usp=sharing
This app records a singing voice in the browser and finds the fundamental
frequency (f0) of each note. It then breaks each note into its harmonic series
(H1, H2, H3 …), with the frequency, musical note, deviation in cents and level
of every harmonic.

## How it works

| Where | What |
|---|---|
| **Browser** (`static/`) | Microphone permission and device choice, level meter, recording (AudioWorklet → 16-bit WAV), playback, rename, download, delete. Takes are stored in the browser's IndexedDB, on the user's own computer. |
| **Server** (`app.py`, `harmonics/`) | `POST /api/analyze` receives one WAV file and returns JSON. The server is stateless and never stores audio. |

Analysis (`harmonics/dsp.py`):

1. Remove DC and apply a 50 Hz high-pass filter.
2. Estimate f0 with YIN (60–1100 Hz) every 10 ms. A noise gate and a voicing check skip silent and unvoiced frames, and an octave-error check guards against strong upper harmonics.
3. Split the pitch track into notes. Vibrato stays one note; real note changes split.
4. For each note, run a zero-padded FFT with parabolic peak interpolation and measure every harmonic n·f0 up to 8 kHz.

Note names come from MIDI numbers, with C as pitch class 0. A4 is configurable,
names use both spellings (C#/Db) and an optional French notation (Do Ré Mi).

## Run locally (Windows)

```bash
cd "D:\voice harmonics\code"
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python app.py
```

Then open **http://127.0.0.1:5000** (or http://localhost:5000) in Chrome, Edge
or Firefox.

1. Click **Enable microphone** and allow access. Choose a device in the list.
   The level meter should move when you sing.
2. Type a name if you like, then click **● Record**. Sing a steady vowel for 2–5 s
   and click **■ Stop** (or press Esc). Record as many takes as you want.
3. Play each take with its audio player. Rename, **Download** or **Delete** takes
   as needed, or use **Delete all**.
4. Click **Analyse** on a take. Click a row in *Notes found* to see that note's
   spectrum and harmonic table.

### If the microphone does not work

- **Windows settings:** in Settings → Privacy & security → Microphone, switch on
  *Microphone access*, *Let apps access your microphone* and *Let desktop apps
  access your microphone*.
- **Browser permission:** click the icon left of the address bar and allow the
  microphone for this site.
- **"Pure silence" message:** the device is muted or blocked. Pick another one
  in the list.
- **Device in use:** close apps that hold the microphone exclusively (some DAWs
  or Teams settings), then click **Rescan**.
- **Wrong address:** browsers allow the microphone only on `https://` or
  `localhost`. A LAN address such as `http://192.168.x.x:5000` is blocked.

## Tests

```bash
.venv\Scripts\python -m pytest -q
```

The tests use synthetic signals, so they need no microphone. They cover:

- note naming (including the old "D#4 for C4" bug);
- pure tone;
- a piano-like tone with a louder H2;
- a missing fundamental;
- overtone singing;
- vibrato;
- noise and silence;
- mains hum;
- sample-rate independence;
- vocal range limits;
- legato steps;
- harmonic precision;
- phantom harmonics;
- the HTTP API.

## Deploy to the internet

The server needs **HTTPS**, because browsers block the microphone on plain
http. Every common host (Render, Railway, Fly.io, Heroku, a VPS behind Caddy or
nginx) provides it.

- **Procfile hosts** (Render, Railway, Heroku): a `Procfile` is included. The
  start command is
  `gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT`.
- **Docker hosts:** a `Dockerfile` is included.
  `docker build -t voice-harmonics .` then
  `docker run -p 8000:8000 voice-harmonics`.
- **PythonAnywhere / WSGI:** point the WSGI file to `from app import app as application`.

Uploads are limited to 40 MB (`MAX_UPLOAD_MB` in `app.py`). Recordings are
limited to 120 s in the browser and 180 s on the server. Analysis time,
measured on the development PC: about 0.3 s for a 5 s take and about 4 s for a
60 s take with 30 notes. Add a rate limit (for example Flask-Limiter or your
host's proxy) before you make the app public.

## Files

```
app.py                 Flask server (static files + /api/analyze)
harmonics/notes.py     frequency ↔ note name / cents
harmonics/dsp.py       YIN pitch tracking, segmentation, harmonic measurement
harmonics/wavio.py     WAV decoding (8/16/24/32-bit int, float, stereo → mono)
static/index.html      page
static/app.js          microphone, recording, take management, plots
static/recorder-worklet.js  PCM capture in the audio thread
static/style.css       styles (light/dark)
tests/                 pytest suite
```
