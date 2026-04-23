"""
Sahayak Health WhatsApp Chatbot
================================
Full patient onboarding + medicine reminders + health check-ins via Twilio WhatsApp
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

app = Flask(__name__)

# ─── Twilio Credentials ───────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "YOUR_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN",  "YOUR_AUTH_TOKEN")
TWILIO_WA_NUMBER   = os.environ.get("TWILIO_WA_NUMBER",   "whatsapp:+14155238886")  # Sandbox number

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ─── Simple JSON-based database ───────────────────────────────────────────────
DB_FILE = "data/patients.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    os.makedirs("data", exist_ok=True)
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

# ─── Send proactive WhatsApp message ──────────────────────────────────────────
def send_wa(to_number, message):
    """Send a message to a WhatsApp user."""
    try:
        client.messages.create(
            body=message,
            from_=TWILIO_WA_NUMBER,
            to=f"whatsapp:{to_number}"
        )
        print(f"[✓] Sent to {to_number}: {message[:60]}...")
    except Exception as e:
        print(f"[✗] Failed to send to {to_number}: {e}")

# ─── Reminder Scheduler ───────────────────────────────────────────────────────
def parse_time(time_str):
    """Parse '08:00 AM' or '8:00' into a datetime.time object."""
    for fmt in ["%I:%M %p", "%H:%M", "%I %p"]:
        try:
            return datetime.strptime(time_str.strip(), fmt).time()
        except:
            continue
    return None

def reminder_loop():
    """Background thread — checks every 60 seconds for due reminders."""
    print("[⏰] Reminder scheduler started...")
    while True:
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")

        db = load_db()
        for phone, patient in db.items():
            if patient.get("step") != "done":
                continue

            medicines = patient.get("medicines", [])
            for med in medicines:
                for dose_time in med.get("times", []):
                    parsed = parse_time(dose_time)
                    if not parsed:
                        continue

                    # Check if this minute matches dose time
                    dose_str = parsed.strftime("%H:%M")
                    if dose_str == current_time_str:
                        # Avoid duplicate reminders (check last_sent)
                        last_key = f"last_sent_{med['name']}_{dose_str}"
                        last_sent = patient.get(last_key)
                        today_str = now.strftime("%Y-%m-%d")

                        if last_sent != today_str:
                            msg = (
                                f"⏰ *Medicine Reminder* — Sahayak\n\n"
                                f"Namaste {patient['name']}! 🌿\n\n"
                                f"💊 *{med['name']}* ({med.get('dose','')}) lene ka time ho gaya!\n"
                                f"🕐 Time: {dose_time}\n\n"
                                f"Kya aapne li? Reply karo:\n"
                                f"✅ *haan* — li gayi\n"
                                f"❌ *nahi* — nahi li abhi"
                            )
                            send_wa(phone.replace("whatsapp:", ""), msg)

                            # Mark as sent today
                            db[phone][last_key] = today_str
                            save_db(db)

            # Health check-in every 6 hours
            last_checkin = patient.get("last_checkin")
            if last_checkin:
                last_dt = datetime.fromisoformat(last_checkin)
                if (now - last_dt).total_seconds() >= 6 * 3600:
                    msg = (
                        f"💬 *Health Check-in* — Sahayak\n\n"
                        f"Namaste {patient['name']}! Aap abhi kaisa feel kar rahe hain?\n\n"
                        f"Reply karo:\n"
                        f"🟢 *better* — theek ho raha hoon\n"
                        f"🟡 *same* — koi change nahi\n"
                        f"🔴 *worse* — kharab lag raha hai"
                    )
                    send_wa(phone.replace("whatsapp:", ""), msg)
                    db[phone]["last_checkin"] = now.isoformat()
                    save_db(db)

        time.sleep(60)  # Check every minute

# ─── Chatbot Logic ────────────────────────────────────────────────────────────
def get_reply(phone, raw_msg):
    db = load_db()
    patient = db.get(phone, {})
    msg = raw_msg.strip().lower()
    step = patient.get("step", "new")

    # ── NEW USER: Start onboarding ────────────────────────────────────────────
    if step == "new" or not patient:
        db[phone] = {
            "step": "ask_name",
            "name": "",
            "age": "",
            "doctor": "",
            "diagnosis": "",
            "medicines": [],
            "med_adding": 0,
            "health_log": [],
            "last_checkin": datetime.now().isoformat()
        }
        save_db(db)
        return (
            "🌿 *Sahayak Health Chatbot mein aapka swagat hai!*\n\n"
            "Main aapko doctor ki advice follow karne mein madad karunga —\n"
            "medicine reminders, health check-ins, aur progress tracking.\n\n"
            "Chaliye shuru karte hain! 😊\n\n"
            "👤 Aapka *poora naam* kya hai?"
        )

    # ── ONBOARDING STEPS ──────────────────────────────────────────────────────
    elif step == "ask_name":
        patient["name"] = raw_msg.strip().title()
        patient["step"] = "ask_age"
        db[phone] = patient
        save_db(db)
        return f"Bahut achha, {patient['name']}! 🙏\n\n📅 Aapki *age* kya hai?"

    elif step == "ask_age":
        patient["age"] = raw_msg.strip()
        patient["step"] = "ask_doctor"
        db[phone] = patient
        save_db(db)
        return "👨‍⚕️ Aapne *kis doctor se dikhaya* hai? (Naam batao)"

    elif step == "ask_doctor":
        patient["doctor"] = raw_msg.strip().title()
        patient["step"] = "ask_diagnosis"
        db[phone] = patient
        save_db(db)
        return (
            f"Dr. {patient['doctor']} — noted! ✅\n\n"
            f"🏥 Doctor ne *kya diagnosis* diya? (kya problem bataya)\n"
            f"Example: Viral fever, Typhoid, Cough & cold..."
        )

    elif step == "ask_diagnosis":
        patient["diagnosis"] = raw_msg.strip()
        patient["step"] = "ask_med_count"
        db[phone] = patient
        save_db(db)
        return (
            f"Theek hai, *{patient['diagnosis']}* — note ho gaya. 📋\n\n"
            f"💊 Doctor ne kul *kitni medicines* di hain?\n"
            f"(Sirf number batao, jaise: 2)"
        )

    elif step == "ask_med_count":
        try:
            count = int(raw_msg.strip())
            if count < 1 or count > 10:
                return "Kripya 1 se 10 ke beech number batao."
            patient["med_count"] = count
            patient["med_adding"] = 0
            patient["medicines"] = []
            patient["step"] = "add_med_name"
            db[phone] = patient
            save_db(db)
            idx = patient["med_adding"] + 1
            return (
                f"Theek hai! {count} medicines add karenge. 💊\n\n"
                f"*Medicine {idx} ka naam* kya hai?\n"
                f"Example: Paracetamol, Amoxicillin..."
            )
        except:
            return "Sirf number batao. Jaise: 2"

    elif step == "add_med_name":
        idx = patient["med_adding"]
        if len(patient["medicines"]) <= idx:
            patient["medicines"].append({})
        patient["medicines"][idx]["name"] = raw_msg.strip().title()
        patient["step"] = "add_med_dose"
        db[phone] = patient
        save_db(db)
        return (
            f"💊 *{patient['medicines'][idx]['name']}* — achha!\n\n"
            f"📏 Is medicine ki *dose* kya hai?\n"
            f"Example: 500mg, 250mg, 1 tablet..."
        )

    elif step == "add_med_dose":
        idx = patient["med_adding"]
        patient["medicines"][idx]["dose"] = raw_msg.strip()
        patient["step"] = "add_med_times"
        db[phone] = patient
        save_db(db)
        return (
            f"*Kitni baar* leni hai aur *kab* leni hai?\n\n"
            f"Example: _08:00 AM, 02:00 PM, 08:00 PM_\n"
            f"(Comma se alag karo)"
        )

    elif step == "add_med_times":
        idx = patient["med_adding"]
        times = [t.strip() for t in raw_msg.split(",")]
        patient["medicines"][idx]["times"] = times
        patient["med_adding"] += 1

        if patient["med_adding"] < patient["med_count"]:
            patient["step"] = "add_med_name"
            db[phone] = patient
            save_db(db)
            next_idx = patient["med_adding"] + 1
            return (
                f"✅ Medicine {idx+1} save ho gayi!\n\n"
                f"*Medicine {next_idx} ka naam* kya hai?"
            )
        else:
            # All medicines added — show summary
            patient["step"] = "done"
            db[phone] = patient
            save_db(db)

            med_list = ""
            for i, m in enumerate(patient["medicines"], 1):
                times_str = ", ".join(m.get("times", []))
                med_list += f"{i}. 💊 *{m['name']}* {m.get('dose','')} — {times_str}\n"

            return (
                f"🎉 *Profile complete ho gayi!*\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 *Naam:* {patient['name']}\n"
                f"📅 *Age:* {patient['age']}\n"
                f"👨‍⚕️ *Doctor:* Dr. {patient['doctor']}\n"
                f"🏥 *Problem:* {patient['diagnosis']}\n\n"
                f"💊 *Medicines:*\n{med_list}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"Ab se main aapko:\n"
                f"⏰ Medicine reminders doonga\n"
                f"💬 Har 6 ghante health check-in karunga\n\n"
                f"Koi bhi help ke liye *menu* type karo 👇"
            )

    # ── MAIN CHATBOT (step == done) ───────────────────────────────────────────

    elif step == "done":

        # Medicine taken / not taken
        if msg in ["haan", "ha", "yes", "li", "le li"]:
            now = datetime.now().strftime("%d %b %Y, %I:%M %p")
            patient.setdefault("health_log", []).append({
                "type": "medicine_taken",
                "time": now
            })
            db[phone] = patient
            save_db(db)
            return (
                f"✅ *Medicine li gayi* — log ho gaya!\n\n"
                f"Shabash {patient['name']}! 💪\n"
                f"Doctor ki advice follow karte raho. Jaldi theek ho jaoge!"
            )

        elif msg in ["nahi", "no", "nhi", "abhi nahi"]:
            return (
                f"⚠️ {patient['name']}, medicine lena mat bhoolna!\n\n"
                f"💊 *Abhi le lo* — ye zaroori hai.\n"
                f"30 min mein phir reminder aayega.\n\n"
                f"_Doctor ki advice follow karna bahut important hai._"
            )

        # Health check-in responses
        elif msg in ["better", "theek", "better hoon", "accha"]:
            now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
            patient.setdefault("health_log", []).append({
                "type": "checkin", "status": "better", "time": now_str
            })
            patient["last_checkin"] = datetime.now().isoformat()
            db[phone] = patient
            save_db(db)
            return (
                f"🟢 *Bahut achha!* Recovery ho rahi hai! 🎉\n\n"
                f"Kuch zaruri tips:\n"
                f"💧 Paani aur fluids lete raho\n"
                f"🛏️ Kafi aaram karo\n"
                f"💊 Medicine schedule follow karo\n\n"
                f"Agle check-in tak khayal rakhna! 🌿"
            )

        elif msg in ["same", "koi change nahi", "wahi"]:
            patient["last_checkin"] = datetime.now().isoformat()
            db[phone] = patient
            save_db(db)
            return (
                f"🟡 Theek hai. Dhairya rakho! 🙏\n\n"
                f"Dr. {patient['doctor']} ki advice follow karte raho.\n"
                f"Agar 2 din mein improvement na aaye, doctor se dobara mile.\n\n"
                f"💊 Medicine time pe lena zaroori hai!"
            )

        elif msg in ["worse", "bura", "kharab", "takleef"]:
            patient["last_checkin"] = datetime.now().isoformat()
            patient.setdefault("health_log", []).append({
                "type": "checkin", "status": "worse",
                "time": datetime.now().strftime("%d %b %Y, %I:%M %p")
            })
            db[phone] = patient
            save_db(db)
            return (
                f"🔴 *Condition kharab ho rahi hai!*\n\n"
                f"⚠️ In symptoms par dhyan do:\n"
                f"❌ Saans lena mushkil\n"
                f"❌ Chest mein dard\n"
                f"❌ Bahut tej bukhar (104°F+)\n"
                f"❌ Hosh kho jana\n\n"
                f"👉 *TURANT Dr. {patient['doctor']} ko call karo*\n"
                f"📞 Emergency: *108*\n"
                f"📞 AIIMS Helpline: *1800-116-117*"
            )

        # Menu / help
        elif msg in ["menu", "help", "options", "kya kar sakte ho"]:
            return (
                f"🌿 *Sahayak Menu*\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📋 *profile* — apni details dekho\n"
                f"💊 *medicines* — medicine schedule dekho\n"
                f"📊 *progress* — health log dekho\n"
                f"💬 *kaisa* — health check-in karo\n"
                f"🚨 *emergency* — emergency info\n"
                f"🔄 *reset* — profile dobara banao\n"
                f"━━━━━━━━━━━━━━━"
            )

        elif msg in ["profile", "meri details", "info"]:
            med_list = ""
            for i, m in enumerate(patient.get("medicines", []), 1):
                times_str = ", ".join(m.get("times", []))
                med_list += f"  {i}. {m['name']} {m.get('dose','')} — {times_str}\n"
            return (
                f"📋 *Aapki Profile*\n\n"
                f"👤 {patient['name']} (Age: {patient['age']})\n"
                f"👨‍⚕️ Dr. {patient['doctor']}\n"
                f"🏥 {patient['diagnosis']}\n\n"
                f"💊 *Medicines:*\n{med_list}"
            )

        elif msg in ["medicines", "medicine", "schedule", "kya leni hai"]:
            now_hour = datetime.now().hour
            lines = []
            for m in patient.get("medicines", []):
                times_str = ", ".join(m.get("times", []))
                lines.append(f"💊 *{m['name']}* {m.get('dose','')} — {times_str}")
            med_block = "\n".join(lines) if lines else "Koi medicine add nahi hui."
            return (
                f"⏰ *Medicine Schedule*\n\n"
                f"{med_block}\n\n"
                f"_Reminder automatically aayega har dose ke waqt._"
            )

        elif msg in ["progress", "log", "history", "kya hua"]:
            logs = patient.get("health_log", [])
            if not logs:
                return "Abhi tak koi health log nahi hai. Check-in karte raho!"
            lines = []
            for entry in logs[-8:]:  # Last 8 entries
                if entry["type"] == "medicine_taken":
                    lines.append(f"✅ Medicine li — {entry['time']}")
                elif entry["type"] == "checkin":
                    emoji = {"better": "🟢", "same": "🟡", "worse": "🔴"}.get(entry["status"], "⚪")
                    lines.append(f"{emoji} Condition: {entry['status']} — {entry['time']}")
            return (
                f"📊 *Health Progress Log*\n\n"
                + "\n".join(lines)
                + f"\n\n_Dr. {patient['doctor']} ki advice follow karte raho!_"
            )

        elif msg in ["kaisa", "check in", "health", "feel"]:
            patient["last_checkin"] = datetime.now().isoformat()
            db[phone] = patient
            save_db(db)
            return (
                f"💬 *Health Check-in*\n\n"
                f"Namaste {patient['name']}! Abhi kaisa feel ho raha hai?\n\n"
                f"🟢 *better* — improving hoon\n"
                f"🟡 *same* — koi change nahi\n"
                f"🔴 *worse* — kharab lag raha hai"
            )

        elif msg in ["emergency", "danger", "help me"]:
            return (
                f"🚨 *EMERGENCY INFO*\n\n"
                f"Turant in par call karo:\n\n"
                f"📞 *Ambulance: 108*\n"
                f"📞 *AIIMS: 1800-116-117*\n"
                f"📞 *Dr. {patient['doctor']}* — apne doctor ka number\n\n"
                f"⚠️ Ye symptoms serious hain — turant jayen:\n"
                f"• Saans lena mushkil\n"
                f"• Chest pain\n"
                f"• Hosh kho jana\n"
                f"• Bahut tej bukhar 104°F+"
            )

        elif msg in ["reset", "dobara", "new"]:
            db[phone] = {"step": "new"}
            save_db(db)
            return "🔄 Profile reset ho gayi. *Sahayak* type karo nayi profile banane ke liye."

        else:
            return (
                f"Samajh nahi aaya 😅\n\n"
                f"*menu* type karo sab options dekhne ke liye, {patient['name']}!"
            )

    return "Kuch galat ho gaya. *menu* type karo."

# ─── Webhook Route ────────────────────────────────────────────────────────────
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    phone = request.form.get("From", "")       # e.g. whatsapp:+919876543210
    body  = request.form.get("Body", "").strip()

    # Use phone without prefix as key
    phone_key = phone.replace("whatsapp:", "")

    print(f"[MSG] {phone_key}: {body}")
    reply_text = get_reply(phone_key, body)

    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "✅ Sahayak WhatsApp Bot is running!"

# ─── Start ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Start reminder thread
    t = threading.Thread(target=reminder_loop, daemon=True)
    t.start()

    print("\n🌿 Sahayak Health Bot starting...")
    print("📡 Webhook: POST /whatsapp")
    print("⏰ Reminder scheduler: running in background\n")
    app.run(debug=False, port=5000)
