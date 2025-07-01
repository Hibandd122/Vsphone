from flask import Flask, render_template_string, redirect, url_for, jsonify, request
import json, os, requests, random, string, threading
from datetime import datetime, timedelta, timezone
import time

app = Flask(__name__)
PASSWORD = "quynhduy23"
ACCOUNT_FILE = "accounts.json"
LOCAL_STORAGE_FILE = "local_storage.txt"

EMAIL_USERNAME = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
EMAIL_DOMAIN = ""
EMAIL_BASE = ""
running = True

def delay(): time.sleep(1)

def get_mail_domain():
    domains = requests.get("https://api.mail.tm/domains").json()["hydra:member"]
    return random.choice(domains)["domain"]

def create_mail_account():
    global EMAIL_DOMAIN, EMAIL_BASE
    EMAIL_DOMAIN = get_mail_domain()
    EMAIL_BASE = f"{EMAIL_USERNAME}@{EMAIL_DOMAIN}"
    while True:
        try:
            payload = {"address": EMAIL_BASE, "password": PASSWORD}
            r = requests.post("https://api.mail.tm/accounts", json=payload)
            if r.status_code == 201:
                while True:
                    t = requests.post("https://api.mail.tm/token", json=payload).json()
                    if "token" in t:
                        return t["token"]
                    delay()
        except:
            delay()

def gen_email_alias():
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{EMAIL_USERNAME}+{suffix}@{EMAIL_DOMAIN}"

def send_sms(email_alias):
    while True:
        try:
            data = {"smsType": 2, "mobilePhone": email_alias, "captchaVerifyParam": json.dumps({"data": ""})}
            h = {"Content-Type": "application/json"}
            r = requests.post("https://api.vsphone.com/vsphone/api/sms/smsSend", json=data, headers=h)
            if r.status_code == 200:
                return
            delay()
        except:
            delay()

def wait_for_code(token, alias):
    h = {"Authorization": f"Bearer {token}"}
    while True:
        try:
            msgs = requests.get("https://api.mail.tm/messages", headers=h).json().get("hydra:member", [])
            for m in msgs:
                recipients = [to['address'] for to in m.get("to", [])]
                if any(alias.lower() == to.lower() for to in recipients) and "VSPhone" in m["subject"]:
                    msg = requests.get(f"https://api.mail.tm/messages/{m['id']}", headers=h).json()
                    for line in msg.get("text", "").splitlines():
                        if line.strip().isdigit() and len(line.strip()) == 6:
                            return line.strip()
            delay()
        except:
            delay()

def login(email_alias, code):
    while True:
        try:
            payload = {
                "mobilePhone": email_alias, "loginType": 0, "verifyCode": code,
                "password": "526a97afaa842892fa91dcc5f9a23d91",
                "channel": "vsagoxch3o"
            }
            headers = {
                "accept": "*/*", "appversion": "1009001", "clienttype": "web", "channel": "vsagoxch3o",
                "content-type": "application/json", "user-agent": "Mozilla/5.0", "userid": "0"
            }
            r = requests.post("https://api.vsphone.com/vsphone/api/user/login", json=payload, headers=headers)
            if r.status_code == 200 and "data" in r.json():
                data = r.json()["data"]
                return data["userId"], data["token"]
            delay()
        except:
            delay()

def save_account(email_alias, uid, token):
    new_entry = {
        "email": email_alias,
        "password": PASSWORD,
        "userId": uid,
        "token": token,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    try:
        if os.path.exists(ACCOUNT_FILE):
            with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
    except:
        data = []
    data.append(new_entry)
    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    with open(LOCAL_STORAGE_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"localStorage.setItem('token', '{token}');\n"
            f"localStorage.setItem('userid', '{uid}');\n"
            f"window.location.reload();\n"
            f"__________________________________________\n"
        )

def background_worker():
    token = create_mail_account()
    while running:
        try:
            alias = gen_email_alias()
            send_sms(alias)
            code = wait_for_code(token, alias)
            uid, user_token = login(alias, code)
            save_account(alias, uid, user_token)
            print(f"{alias}:{PASSWORD}\n{uid}\n{user_token}\n__________________________________________")
        except Exception as e:
            print("❌ Lỗi:", e)
        delay()

@app.route("/")
def index():
    html = """<html><head><meta http-equiv='refresh' content='0; URL=/accounts' /></head><body></body></html>"""
    return render_template_string(html)

@app.route("/accounts")
def get_accounts():
    try:
        with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
            accounts = json.load(f)
    except:
        accounts = []
    now = datetime.now(timezone.utc)
    for acc in accounts:
        try:
            created = datetime.fromisoformat(acc["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
        except:
            acc["expired"] = True
            acc["remaining"] = "?"
            continue
        elapsed = now - created
        acc["expired"] = elapsed > timedelta(hours=24)
        if not acc["expired"]:
            remaining = timedelta(hours=24) - elapsed
            hrs, rem = divmod(remaining.seconds, 3600)
            mins = rem // 60
            secs = rem % 60
            acc["remaining"] = f"{hrs:02d}h{mins:02d}m{secs:02d}s"
        else:
            acc["remaining"] = "Hết hạn"
    return jsonify(accounts)

@app.route("/cleanup", methods=["POST"])
def cleanup():
    try:
        with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
            accounts = json.load(f)
    except:
        accounts = []
    now = datetime.now(timezone.utc)
    valid_accounts = []
    for acc in accounts:
        try:
            created = datetime.fromisoformat(acc["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if now - created <= timedelta(hours=24):
                valid_accounts.append(acc)
        except:
            continue
    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(valid_accounts, f, indent=2, ensure_ascii=False)
    return redirect(url_for("get_accounts"))

@app.route("/clean", methods=["POST"])
def clean_by_email():
    email = request.json.get("email")
    if not email:
        return jsonify({"error": "Missing email"}), 400
    try:
        with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
            accounts = json.load(f)
    except:
        accounts = []
    accounts = [acc for acc in accounts if acc.get("email") != email]
    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)
    return jsonify({"status": "deleted", "email": email})

if __name__ == "__main__":
    threading.Thread(target=background_worker, daemon=True).start()
