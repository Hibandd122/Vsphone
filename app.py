from flask import Flask, jsonify
import requests, time, json, random, string

app = Flask(__name__)
PASSWORD = "quynhduy23"

def delay(): time.sleep(1)

def get_mail_domain():
    while True:
        try:
            domains = requests.get("https://api.mail.tm/domains").json()["hydra:member"]
            return random.choice(domains)["domain"]
        except:
            delay()

def create_mail_account(email):
    payload = {"address": email, "password": PASSWORD}
    while True:
        try:
            r = requests.post("https://api.mail.tm/accounts", json=payload)
            if r.status_code == 201:
                while True:
                    t = requests.post("https://api.mail.tm/token", json=payload).json()
                    if "token" in t:
                        return t["token"]
                    delay()
        except:
            delay()

def gen_email_alias(base):
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{base}+{suffix}"

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

def wait_for_code(token, alias):
    headers = {"Authorization": f"Bearer {token}"}
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
        base_username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email_domain = get_mail_domain()
        base_email = f"{base_username}@{email_domain}"
        mail_token = create_mail_account(base_email)

        alias = f"{gen_email_alias(base_username)}@{email_domain}"
        send_sms(alias)
        code = wait_for_code(mail_token, alias)
        uid, user_token = login(alias, code)

        return jsonify({
            "userId": uid,
            "token": user_token
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
