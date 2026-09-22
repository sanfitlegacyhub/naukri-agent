"""
Naukri Profile Agent
- Logs in to Naukri
- Uploads latest resume PDF
- Updates profile headline + skills
- Scrapes profile view count
- Sends summary email via Gmail SMTP
"""

import os
import re
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─── Config from environment variables ────────────────────────────────────────
NAUKRI_EMAIL    = os.environ["NAUKRI_EMAIL"]       # santhoshgowda360@gmail.com
NAUKRI_PASSWORD = os.environ["NAUKRI_PASSWORD"]
GMAIL_USER      = os.environ["GMAIL_USER"]         # santhoshramesh.rs@gmail.com
GMAIL_APP_PASS  = os.environ["GMAIL_APP_PASS"]
NOTIFY_EMAIL    = os.environ.get("NOTIFY_EMAIL", "santhoshramesh.rs@gmail.com")
RESUME_PATH     = os.environ.get("RESUME_PATH", "resume/Santhosh_Devops_Engineer.pdf")

# ─── Profile update values ────────────────────────────────────────────────────
# Name          : Santhosh N R
# Location      : Bengaluru, India
# Experience    : 5 Years
# Current CTC   : ₹20,00,000
# Notice Period : 2 Months
# Phone         : 7337686447
PROFILE_HEADLINE = (
    "DevOps Engineer | AWS | Kubernetes | Docker | CI/CD | MFT | IBM | 5 Years"
)
PROFILE_SKILLS = [
    "DevOps", "AWS", "Docker", "Kubernetes", "Jenkins", "GitHub Actions",
    "Python", "Bash", "Terraform", "CI/CD", "Linux", "MFT", "SFTP",
    "Playwright", "Grafana", "Prometheus", "CloudWatch", "EKS",
    "Shell Scripting", "Release Engineering", "Incident Management",
    "Robot Framework", "Karate", "SAST", "DAST", "IAM"
]

# ─── Candidate meta (used in email report) ────────────────────────────────────
CANDIDATE = {
    "name"          : "Santhosh N R",
    "location"      : "Bengaluru, India",
    "experience"    : "5 Years",
    "current_ctc"   : "₹20,00,000",
    "notice_period" : "2 Months",
    "phone"         : "7337686447",
    "email"         : "santhoshgowda360@gmail.com",
}

BASE_URL    = "https://www.naukri.com"
API_BASE    = "https://www.naukri.com/central-login-services/v1"
PROFILE_API = "https://www.naukri.com/profile-services/v1"

HEADERS = {
    "User-Agent" : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept"     : "application/json",
    "appid"      : "109",
    "systemid"   : "Naukri",
}

# ─── Session ──────────────────────────────────────────────────────────────────
session = requests.Session()
session.headers.update(HEADERS)

report = []   # collects log lines for the email report

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    report.append(line)


# ─── Step 1 : Login ───────────────────────────────────────────────────────────
def login() -> str:
    log("Logging in to Naukri...")
    # Debug: confirm secrets loaded correctly (password masked)
    log(f"  NAUKRI_EMAIL    = '{NAUKRI_EMAIL}'")
    log(f"  NAUKRI_PASSWORD = '{'*' * len(NAUKRI_PASSWORD) if NAUKRI_PASSWORD else 'EMPTY!!!'}'")

    resp = session.post(
        f"{API_BASE}/login",
        json={
            "username": NAUKRI_EMAIL,
            "password": NAUKRI_PASSWORD,
        },
        headers={
            **session.headers,
            "Content-Type": "application/json",
            "appid"       : "109",
            "systemid"    : "Naukri",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed — HTTP {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    token = (
        data.get("loginData", {}).get("token")
        or data.get("token")
        or data.get("data", {}).get("token")
    )
    if not token:
        # try to pull from cookies
        token = session.cookies.get("nauk_at") or session.cookies.get("nk")

    if token:
        session.headers["Authorization"] = f"Bearer {token}"
        log("Login successful ✅")
    else:
        log("Login succeeded but no token found — continuing with cookie session")

    return token or ""


# ─── Step 2 : Upload Resume ───────────────────────────────────────────────────
def upload_resume() -> bool:
    if not os.path.exists(RESUME_PATH):
        log(f"Resume not found at '{RESUME_PATH}' — skipping upload ⚠️")
        return False

    log(f"Uploading resume: {RESUME_PATH} ...")
    file_size = os.path.getsize(RESUME_PATH)
    log(f"  File size: {file_size / 1024:.1f} KB")

    with open(RESUME_PATH, "rb") as f:
        files = {
            "resume": (os.path.basename(RESUME_PATH), f, "application/pdf"),
        }
        upload_headers = {k: v for k, v in session.headers.items() if k != "Content-Type"}
        resp = session.post(
            f"{PROFILE_API}/resume",
            files=files,
            headers=upload_headers,
            timeout=60,
        )

    if resp.status_code in (200, 201):
        log("Resume uploaded successfully ✅")
        return True
    else:
        log(f"Resume upload failed — HTTP {resp.status_code}: {resp.text[:300]} ⚠️")
        return False


# ─── Step 3 : Update Profile Headline & Skills ────────────────────────────────
def update_profile() -> bool:
    log("Updating profile headline and skills...")
    payload = {
        "headline": PROFILE_HEADLINE,
        "keySkills": PROFILE_SKILLS,
    }
    resp = session.patch(
        f"{PROFILE_API}/profile",
        json=payload,
        timeout=30,
    )
    if resp.status_code in (200, 201, 204):
        log("Profile updated successfully ✅")
        return True
    else:
        log(f"Profile update failed — HTTP {resp.status_code}: {resp.text[:300]} ⚠️")
        return False


# ─── Step 4 : Fetch Profile View Stats ────────────────────────────────────────
def fetch_profile_stats() -> dict:
    log("Fetching profile view stats...")
    stats = {}

    # Dashboard endpoint (internal — may change with Naukri updates)
    resp = session.get(
        "https://www.naukri.com/jobseeker/trackings",
        timeout=30,
    )

    if resp.status_code == 200:
        try:
            data = resp.json()
            stats["profile_views"]    = data.get("profileViews",    data.get("views", "N/A"))
            stats["resume_downloads"] = data.get("resumeDownloads", data.get("downloads", "N/A"))
            stats["recruiter_actions"]= data.get("recruiterActions","N/A")
            log(f"  Profile views     : {stats['profile_views']}")
            log(f"  Resume downloads  : {stats['resume_downloads']}")
            log(f"  Recruiter actions : {stats['recruiter_actions']}")
        except Exception:
            log("Could not parse stats JSON — logging raw snippet")
            # fallback: scrape numbers from HTML/text
            numbers = re.findall(r'"(?:profileViews|views|downloads)"\s*:\s*(\d+)', resp.text)
            stats["raw_numbers"] = numbers
            log(f"  Raw numbers found : {numbers}")
    else:
        log(f"Stats fetch failed — HTTP {resp.status_code} ⚠️")

    return stats


# ─── Step 5 : Send Email Report ───────────────────────────────────────────────
def send_email(stats: dict, resume_ok: bool, profile_ok: bool):
    log("Sending email report...")

    run_date = datetime.now().strftime("%d %b %Y %I:%M %p IST")
    status   = "✅ All steps completed" if (resume_ok and profile_ok) else "⚠️ Some steps had issues"

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;font-size:14px;color:#1f2328;max-width:700px;margin:auto">
    <h2 style="color:#3b82d4">Naukri Profile Agent — Daily Report</h2>
    <p><b>Run Date:</b> {run_date} &nbsp;|&nbsp; <b>Status:</b> {status}</p>
    <hr/>

    <h3>👤 Candidate Profile</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
      <tr style="background:#f7f8fa"><th>Field</th><th>Value</th></tr>
      <tr><td>Name</td><td>{CANDIDATE["name"]}</td></tr>
      <tr><td>Location</td><td>{CANDIDATE["location"]}</td></tr>
      <tr><td>Experience</td><td>{CANDIDATE["experience"]}</td></tr>
      <tr><td>Current CTC</td><td>{CANDIDATE["current_ctc"]}</td></tr>
      <tr><td>Notice Period</td><td>{CANDIDATE["notice_period"]}</td></tr>
      <tr><td>Phone</td><td>{CANDIDATE["phone"]}</td></tr>
      <tr><td>Naukri Email</td><td>{CANDIDATE["email"]}</td></tr>
      <tr><td>Updated Headline</td><td>{PROFILE_HEADLINE}</td></tr>
    </table>

    <h3>⚙️ Actions Performed</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
      <tr style="background:#f7f8fa"><th>Action</th><th>Result</th></tr>
      <tr><td>Login</td><td>✅ Success</td></tr>
      <tr><td>Resume Upload</td><td>{"✅ Uploaded — Last Updated reset to Today" if resume_ok else "⚠️ Skipped / Failed"}</td></tr>
      <tr><td>Profile Headline + Skills Update</td><td>{"✅ Updated" if profile_ok else "⚠️ Failed"}</td></tr>
    </table>

    <h3>📊 Profile Stats</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
      <tr style="background:#f7f8fa"><th>Metric</th><th>Value</th></tr>
      <tr><td>Profile Views</td><td>{stats.get("profile_views", "N/A")}</td></tr>
      <tr><td>Resume Downloads</td><td>{stats.get("resume_downloads", "N/A")}</td></tr>
      <tr><td>Recruiter Actions</td><td>{stats.get("recruiter_actions", "N/A")}</td></tr>
    </table>

    <h3>📋 Run Log</h3>
    <pre style="background:#f7f8fa;padding:12px;font-size:12px;border:1px solid #e5e7eb">{"<br>".join(report)}</pre>
    <hr/>
    <p style="font-size:11px;color:#57606a;text-align:center">
      Naukri Agent &bull; Runs daily at 9 AM IST &bull;
      <a href="https://www.naukri.com/mnjuser/profile">Open Your Naukri Profile</a>
    </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Naukri Agent Report — {run_date}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        server.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())

    log(f"Email sent to {NOTIFY_EMAIL} ✅")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    log("=" * 50)
    log("Naukri Profile Agent Starting")
    log("=" * 50)

    login()
    resume_ok  = upload_resume()
    profile_ok = update_profile()
    stats      = fetch_profile_stats()
    send_email(stats, resume_ok, profile_ok)

    log("=" * 50)
    log("Agent run complete")
    log("=" * 50)


if __name__ == "__main__":
    main()
