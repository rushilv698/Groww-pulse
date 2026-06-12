"""
Flask wrapper that serves the prototype UI and exposes /api/pulse.
"""
import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

HERE = Path(__file__).parent
PARENT = HERE.parent
sys.path.append(str(PARENT))

# Now we can import from the parent directory
from pulse import run_pulse

app = Flask(__name__, static_folder=str(HERE), static_url_path="")


@app.get("/")
def index():
    return send_from_directory(HERE, "Groww-Pulse Weekly.html")

@app.get("/api/latest")
def latest_pulse():
    try:
        note_path = PARENT / "weekly_note.md"
        csv_path = PARENT / "sample_reviews.csv"
        
        note = ""
        if note_path.exists():
            note = note_path.read_text(encoding="utf-8")
            
        count = 0
        if csv_path.exists():
            lines = csv_path.read_text(encoding="utf-8").strip().split('\n')
            count = max(0, len(lines) - 1)
            
        return jsonify({"ok": True, "note": note, "count": count})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/pulse")
def pulse():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    if not email or "@" not in email:
        return jsonify({"ok": False, "error": "invalid email"}), 400

    try:
        # === PLUG IN YOUR BACKEND HERE ===
        summary, opening, count, structured_data = run_pulse(recipient_email=email)
        # =================================
        return jsonify({"ok": True, "email": email, "note": summary, "opening": opening, "count": count, "structured_data": structured_data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
