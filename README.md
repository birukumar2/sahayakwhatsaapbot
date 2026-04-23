# 🌿 Sahayak WhatsApp Health Chatbot
### Patient Reminder System — Twilio + Python

---

## Features (Kya karta hai)

| Feature | Details |
|---|---|
| ✅ Patient Onboarding | Naam, age, doctor, diagnosis, medicines sab collect karta hai |
| ⏰ Auto Reminders | Har medicine ke time pe automatically WhatsApp message |
| 💬 Health Check-ins | Har 6 ghante automatically poochta hai "kaisa feel ho raha hai" |
| 📊 Progress Log | Medicine li ya nahi — sab track hota hai |
| 🚨 Emergency Alert | "Worse" reply pe turant hospital/doctor info |
| 📋 Profile View | Patient apni saari details kisi bhi waqt dekh sakta hai |
| 💾 JSON Database | Sab data save hota hai — restart ke baad bhi data rehta hai |

---

## Setup (Step by Step)

### STEP 1 — Python install karo
```
Python 3.9+ chahiye: https://python.org
```

### STEP 2 — Dependencies install karo
```bash
pip install flask twilio
```

### STEP 3 — Twilio setup karo
1. **twilio.com** pe account banao (free — $15 credits milenge)
2. Console mein jaao → **Messaging → Try it out → WhatsApp**
3. Sandbox activate karo
4. Apna **Account SID** aur **Auth Token** copy karo

### STEP 4 — Credentials set karo
`app.py` file mein ye lines edit karo:
```python
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN  = "your_auth_token_here"
TWILIO_WA_NUMBER   = "whatsapp:+14155238886"  # Sandbox number (change mat karo)
```

**YA** environment variables use karo (recommended):
```bash
# Windows
set TWILIO_ACCOUNT_SID=ACxxxx...
set TWILIO_AUTH_TOKEN=xxxx...

# Mac/Linux
export TWILIO_ACCOUNT_SID=ACxxxx...
export TWILIO_AUTH_TOKEN=xxxx...
```

### STEP 5 — Bot chalao
```bash
python app.py
```
Ye dikhega:
```
🌿 Sahayak Health Bot starting...
📡 Webhook: POST /whatsapp
⏰ Reminder scheduler: running in background
```

### STEP 6 — ngrok se internet pe expose karo
Naya terminal kholo:
```bash
# ngrok install karo: https://ngrok.com
ngrok http 5000
```
Tumhe milega kuch aisa:
```
https://abc123.ngrok-free.app
```

### STEP 7 — Twilio mein webhook set karo
1. Twilio Console → **Messaging → WhatsApp Sandbox Settings**
2. "When a message comes in" field mein daalo:
```
https://abc123.ngrok-free.app/whatsapp
```
3. HTTP POST select karo → Save

### STEP 8 — Test karo!
1. Apne WhatsApp se Sandbox number pe message karo:
   ```
   join <your-sandbox-code>
   ```
   (Code Twilio Console mein dikhega)
2. Join confirmation aane ke baad — koi bhi message bhejo
3. Bot reply karega! 🎉

---

## User Flow (Patient ka experience)

```
Patient: "Hi"
Bot: "Sahayak mein swagat hai! Naam kya hai?"

Patient: "Ravi Kumar"
Bot: "Age kya hai?"

Patient: "34"
Bot: "Doctor ka naam?"

Patient: "Dr. Meena Sharma"
Bot: "Diagnosis kya hai?"

Patient: "Viral Fever"
Bot: "Kitni medicines hain?"

Patient: "2"
Bot: "Medicine 1 ka naam?"

Patient: "Paracetamol"
Bot: "Dose?"

Patient: "500mg"
Bot: "Kab leni hai? (times)"

Patient: "08:00 AM, 02:00 PM, 08:00 PM"
Bot: "Medicine 2 ka naam?"
... (repeat)

Bot: "🎉 Profile complete! Ab reminders milenge."

--- 6 ghante baad ---
Bot: "💬 Health check-in: kaisa feel ho raha hai? better/same/worse"

--- Medicine time pe ---
Bot: "⏰ Paracetamol 500mg lene ka time! Kya li? haan/nahi"
```

---

## Commands (Patient kya type kar sakta hai)

| Command | Kya hota hai |
|---|---|
| `menu` | Saare options dikhata hai |
| `profile` | Patient ki poori details |
| `medicines` | Medicine schedule |
| `progress` | Health log history |
| `kaisa` | Health check-in shuru karo |
| `emergency` | Emergency numbers |
| `reset` | Profile dobara banao |
| `haan` | Medicine li — log hota hai |
| `nahi` | Medicine nahi li — warning |
| `better/same/worse` | Health status update |

---

## Data Storage

Sab data `data/patients.json` mein save hota hai.
Format:
```json
{
  "+919876543210": {
    "step": "done",
    "name": "Ravi Kumar",
    "age": "34",
    "doctor": "Dr. Meena Sharma",
    "diagnosis": "Viral Fever",
    "medicines": [
      {
        "name": "Paracetamol",
        "dose": "500mg",
        "times": ["08:00 AM", "02:00 PM", "08:00 PM"]
      }
    ],
    "health_log": [
      {"type": "medicine_taken", "time": "24 Apr 2026, 08:02 AM"},
      {"type": "checkin", "status": "better", "time": "24 Apr 2026, 02:05 PM"}
    ],
    "last_checkin": "2026-04-24T14:05:00"
  }
}
```

---

## Production ke liye (future mein)

- [ ] **Free hosting**: Railway.app ya Render.com pe deploy karo (free tier)
- [ ] **Real phone number**: Twilio pe WhatsApp Business number register karo ($1-2/month)
- [ ] **Database**: JSON ki jagah SQLite ya PostgreSQL use karo
- [ ] **Multiple patients**: Already support karta hai — har phone number alag patient

---

## Important Notes

⚠️ Ye chatbot **doctor ki advice replace nahi karta** — sirf follow karne mein help karta hai.
⚠️ Sandbox mein sirf jo log "join" karein unhe hi message ja sakta hai.
⚠️ Free Twilio trial mein 50 messages/day limit hai.
