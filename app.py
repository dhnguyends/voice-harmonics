"""Voice Harmonics Analyzer — web server.

The browser records the voice (microphone selection, playback, storage and
deletion of takes all happen client-side) and posts a WAV file to
/api/analyze.  The server is stateless: it never stores audio.

Local run:   python app.py            -> http://127.0.0.1:5000
Production:  gunicorn app:app         (see README.md)
"""

from __future__ import annotations

import math
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from harmonics import AnalysisError, AudioDecodeError, analyze, read_wav_bytes

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MAX_UPLOAD_MB = 40  # 180 s of 48 kHz 16-bit mono is ~17 MB

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def _float_arg(name: str, default: float, lo: float, hi: float) -> float:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError:
        raise AnalysisError(f"Parameter '{name}' must be a number.")
    if not math.isfinite(value) or not lo <= value <= hi:
        raise AnalysisError(f"Parameter '{name}' must be between {lo} and {hi}.")
    return value


@app.after_request
def _security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Permissions-Policy", "microphone=(self)")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; media-src 'self' blob:; img-src 'self' data:; "
        "style-src 'self'; script-src 'self'; connect-src 'self'",
    )
    return resp


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.post("/api/analyze")
def api_analyze():
    try:
        a4 = _float_arg("a4", 440.0, 400.0, 480.0)
        gate_db = _float_arg("gate", -50.0, -90.0, -10.0)
        upload = request.files.get("audio")
        data = upload.read() if upload else request.get_data(cache=False)
        x, sr = read_wav_bytes(data)
        result = analyze(x, sr, a4=a4, gate_db=gate_db)
    except (AnalysisError, AudioDecodeError) as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(result)


@app.errorhandler(413)
def too_large(_exc):
    return jsonify(error=f"Upload too large (limit {MAX_UPLOAD_MB} MB)."), 413


@app.errorhandler(HTTPException)
def http_error(exc: HTTPException):
    if request.path.startswith("/api/"):
        return jsonify(error=exc.description), exc.code
    return exc


@app.errorhandler(Exception)
def unexpected(exc: Exception):
    app.logger.exception("Unhandled error")
    return jsonify(error="Internal error while analysing the recording."), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    # 127.0.0.1 (not a LAN IP): browsers only allow the microphone on
    # localhost or HTTPS origins.
    print(f"Voice Harmonics Analyzer running on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
