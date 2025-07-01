from flask import Flask, jsonify
from flask_cors import CORS
import requests, time, json, random, string

app = Flask(__name__)
CORS(app)  # Mở CORS cho tất cả domain

PASSWORD = "quynhduy23"
EMAIL_USERNAME = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
EMAIL_DOMAIN = None
EMAIL_BASE = None
MAIL_TOKEN = None

def delay(): time.sleep(1)

def get_mail_domain():
    while True:
        try:
            domains = requests.get("https://api.mail.tm/domains").json()["hydra:member"]
            return random.choice(domains)["domain"]
        except:
            delay()

def create_main_mail():
    global EMAIL_DOMAIN, EMAIL_BASE, MAIL_TOKEN
    EMAIL_DOMAIN = get_mail_domain()
    EMAIL_BASE = f"{EMAIL_USERNAME}@{EMAIL_DOMAIN}"
    payload = {"address": EMAIL_BASE, "password": PASSWORD}

    while True:
        try:
            print(f"[📧] Tạo mail chính: {EMAIL_BASE}")
            r = requests.post("https://api.mail.tm/accounts", json=payload)
            if r.status_code == 201:
                while True:
                    t = requests.post("https://api.mail.tm/token", json=payload).json()
                    if "token" in t:
                        MAIL_TOKEN = t["token"]
                        print("[🔐] Token mail OK")
                        return
                    delay()
        except:
            delay()

def gen_email_alias():
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{EMAIL_USERNAME}+{suffix}@{EMAIL_DOMAIN}"

def send_sms(email_alias):
    data = {"smsType": 2, "mobilePhone": email_alias, "captchaVerifyParam": json.dumps({"data": ""})}
    headers = {"Content-Type": "application/json"}
    while True:
        try:
            r = requests.post("https://api.vsphone.com/vsphone/api/sms/smsSend", json=data, headers=headers)
            if r.status_code == 200:
                return
            delay()
        except:
            delay()

def wait_for_code(alias):
    headers = {"Authorization": f"Bearer {MAIL_TOKEN}"}
    while True:
        try:
            msgs = requests.get("https://api.mail.tm/messages", headers=headers).json().get("hydra:member", [])
            for m in msgs:
                recipients = [to['address'] for to in m.get("to", [])]
                if any(alias.lower() == to.lower() for to in recipients) and "VSPhone" in m["subject"]:
                    msg = requests.get(f"https://api.mail.tm/messages/{m['id']}", headers=headers).json()
                    for line in msg.get("text", "").splitlines():
                        if line.strip().isdigit() and len(line.strip()) == 6:
                            return line.strip()
            delay()
        except:
            delay()

def login(email_alias, code):
    payload = {
        "mobilePhone": email_alias, "loginType": 0, "verifyCode": code,
        "password": "526a97afaa842892fa91dcc5f9a23d91",
        "channel": "vsagoxch3o"
    }
    headers = {
        "accept": "*/*", "appversion": "1009001", "clienttype": "web", "channel": "vsagoxch3o",
        "content-type": "application/json", "user-agent": "Mozilla/5.0", "userid": "0"
    }
    while True:
        try:
            r = requests.post("https://api.vsphone.com/vsphone/api/user/login", json=payload, headers=headers)
            if r.status_code == 200 and "data" in r.json():
                d = r.json()["data"]
                return d["userId"], d["token"]
            delay()
        except:
            delay()

@app.route("/create", methods=["GET"])
def create_account():
    try:
        if MAIL_TOKEN is None:
            return jsonify({"error": "Mail chưa khởi tạo"}), 500

        alias = gen_email_alias()
        send_sms(alias)
        code = wait_for_code(alias)
        uid, user_token = login(alias, code)

        return jsonify({
            "userId": uid,
            "token": user_token
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    create_main_mail()  # tạo mail gốc lúc khởi động
