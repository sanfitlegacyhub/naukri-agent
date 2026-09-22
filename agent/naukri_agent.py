"""
Naukri Profile Agent — Selenium based
- Logs in via real Chrome browser (bypasses bot detection)
- Uploads latest resume PDF
- Updates profile headline
- Sends summary email via Gmail SMTP
"""

import os
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ─── Config from environment variables ────────────────────────────────────────
def _require_env(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        raise EnvironmentError(f"❌ Required secret '{key}' is missing or empty!")
    return val

NAUKRI_EMAIL    = _require_env("NAUKRI_EMAIL")
NAUKRI_PASSWORD = _require_env("NAUKRI_PASSWORD")
GMAIL_USER      = _require_env("GMAIL_USER")
GMAIL_APP_PASS  = _require_env("GMAIL_APP_PASS")
NOTIFY_EMAIL    = os.environ.get("NOTIFY_EMAIL", "santhoshramesh.rs@gmail.com").strip()
RESUME_PATH     = os.environ.get("RESUME_PATH", "resume/Santhosh_Devops_Engineer.pdf").strip()

# Resolve resume path relative to repo root
REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESUME_FULL = os.path.join(REPO_ROOT, RESUME_PATH)

# ─── Profile values ───────────────────────────────────────────────────────────
PROFILE_HEADLINE = "DevOps Engineer | AWS | Kubernetes | Docker | CI/CD | MFT | IBM | 5 Years"

CANDIDATE = {
    "name"          : "Santhosh N R",
    "location"      : "Bengaluru, India",
    "experience"    : "5 Years",
    "current_ctc"   : "₹20,00,000",
    "notice_period" : "2 Months",
    "phone"         : "7337686447",
    "email"         : NAUKRI_EMAIL,
}

# ─── Logging ──────────────────────────────────────────────────────────────────
report = []

def log(msg: str):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    report.append(line)

# Startup config dump
print(f"[CONFIG] NAUKRI_EMAIL    = '{'*' * len(NAUKRI_EMAIL)}'")
print(f"[CONFIG] NAUKRI_PASSWORD = '{'*' * len(NAUKRI_PASSWORD)}'")
print(f"[CONFIG] GMAIL_USER      = '{'*' * len(GMAIL_USER)}'")
print(f"[CONFIG] GMAIL_APP_PASS  = '{'*' * len(GMAIL_APP_PASS)}'")
print(f"[CONFIG] NOTIFY_EMAIL    = '{NOTIFY_EMAIL}'")
print(f"[CONFIG] RESUME_PATH     = '{RESUME_FULL}'")
print(f"[CONFIG] RESUME EXISTS   = '{os.path.exists(RESUME_FULL)}'")

# ─── Browser setup ────────────────────────────────────────────────────────────
def make_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    # Use system Chrome on Mac
    opts.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts,
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver

# ─── Step 1 : Login ───────────────────────────────────────────────────────────
def login(driver: webdriver.Chrome):
    log("Opening Naukri login page...")
    driver.get("https://www.naukri.com/nlogin/login")
    wait = WebDriverWait(driver, 20)

    # Wait for email field
    email_field = wait.until(EC.element_to_be_clickable((By.ID, "usernameField")))
    time.sleep(1)
    email_field.click()
    email_field.clear()
    # Type character by character to avoid bot detection
    for ch in NAUKRI_EMAIL:
        email_field.send_keys(ch)
        time.sleep(0.05)
    log(f"  Email entered: {NAUKRI_EMAIL[:4]}***")

    time.sleep(0.5)

    # Enter password
    pass_field = wait.until(EC.element_to_be_clickable((By.ID, "passwordField")))
    pass_field.click()
    pass_field.clear()
    for ch in NAUKRI_PASSWORD:
        pass_field.send_keys(ch)
        time.sleep(0.05)
    log("  Password entered")

    time.sleep(0.5)

    # Screenshot before clicking login (to see what's on screen)
    screenshot_path = "/tmp/naukri_before_login.png"
    driver.save_screenshot(screenshot_path)
    log(f"  Screenshot saved: {screenshot_path}")

    # Click login button
    login_btn = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[@type='submit' and contains(@class,'login')]")
    ))
    login_btn.click()
    log("  Login button clicked")

    # Wait for redirect
    time.sleep(5)
    current_url = driver.current_url
    log(f"  URL after login: {current_url}")

    # Screenshot after login attempt
    driver.save_screenshot("/tmp/naukri_after_login.png")

    if "nlogin" not in current_url and "login" not in current_url.lower():
        log("Login successful ✅")
        return

    # Still on login page — capture page source for diagnosis
    page_text = driver.find_element(By.TAG_NAME, "body").text[:500]
    log(f"  Page content: {page_text}")
    raise RuntimeError(f"Login failed — still on login page. Body: {page_text[:200]}")

# ─── Step 2 : Upload Resume ───────────────────────────────────────────────────
def upload_resume(driver: webdriver.Chrome) -> bool:
    if not os.path.exists(RESUME_FULL):
        log(f"Resume not found at '{RESUME_FULL}' — skipping ⚠️")
        return False

    log(f"Navigating to profile page for resume upload...")
    driver.get("https://www.naukri.com/mnjuser/profile")
    time.sleep(3)

    try:
        wait = WebDriverWait(driver, 15)
        # Click "Update Resume" button
        upload_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@type='file']")
        ))
        upload_btn.send_keys(RESUME_FULL)
        time.sleep(3)
        log("Resume uploaded successfully ✅")
        return True
    except Exception as e:
        log(f"Resume upload failed: {e} ⚠️")
        return False

# ─── Step 3 : Update Headline ─────────────────────────────────────────────────
def update_headline(driver: webdriver.Chrome) -> bool:
    log("Updating profile headline...")
    try:
        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(3)
        wait = WebDriverWait(driver, 15)

        # Click edit on headline section
        headline_edit = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class,'resumeHeadline')]//span[contains(@class,'edit')]")
        ))
        headline_edit.click()
        time.sleep(1)

        # Find textarea and update
        textarea = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//textarea[contains(@placeholder,'headline') or contains(@class,'headline')]")
        ))
        textarea.clear()
        textarea.send_keys(PROFILE_HEADLINE)
        time.sleep(1)

        # Save
        save_btn = driver.find_element(
            By.XPATH, "//button[contains(text(),'Save') or contains(text(),'save')]"
        )
        save_btn.click()
        time.sleep(2)
        log("Headline updated ✅")
        return True
    except Exception as e:
        log(f"Headline update failed: {e} ⚠️")
        return False

# ─── Step 4 : Fetch Profile Stats ─────────────────────────────────────────────
def fetch_stats(driver: webdriver.Chrome) -> dict:
    log("Fetching profile stats...")
    stats = {"profile_views": "N/A", "resume_downloads": "N/A"}
    try:
        driver.get("https://www.naukri.com/mnjuser/homepage")
        time.sleep(3)
        page = driver.page_source

        import re
        views = re.search(r'"profileViews"\s*:\s*(\d+)', page)
        downloads = re.search(r'"resumeDownloads"\s*:\s*(\d+)', page)

        if views:
            stats["profile_views"] = views.group(1)
        if downloads:
            stats["resume_downloads"] = downloads.group(1)

        log(f"  Profile views    : {stats['profile_views']}")
        log(f"  Resume downloads : {stats['resume_downloads']}")
    except Exception as e:
        log(f"Stats fetch failed: {e} ⚠️")
    return stats

# ─── Step 5 : Send Email ──────────────────────────────────────────────────────
def send_email(stats: dict, resume_ok: bool, headline_ok: bool):
    log("Sending email report...")
    run_date = datetime.now().strftime("%d %b %Y %I:%M %p IST")
    status   = "✅ All steps completed" if (resume_ok and headline_ok) else "⚠️ Some steps had issues"

    html = f"""
    <html><body style="font-family:Arial,sans-serif;font-size:14px;color:#1f2328;max-width:700px;margin:auto">
    <h2 style="color:#3b82d4">Naukri Profile Agent — Daily Report</h2>
    <p><b>Run Date:</b> {run_date} &nbsp;|&nbsp; <b>Status:</b> {status}</p>
    <hr/>
    <h3>👤 Candidate</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
      <tr style="background:#f7f8fa"><th>Field</th><th>Value</th></tr>
      <tr><td>Name</td><td>{CANDIDATE['name']}</td></tr>
      <tr><td>Location</td><td>{CANDIDATE['location']}</td></tr>
      <tr><td>Experience</td><td>{CANDIDATE['experience']}</td></tr>
      <tr><td>Current CTC</td><td>{CANDIDATE['current_ctc']}</td></tr>
      <tr><td>Notice Period</td><td>{CANDIDATE['notice_period']}</td></tr>
      <tr><td>Headline Set</td><td>{PROFILE_HEADLINE}</td></tr>
    </table>
    <h3>⚙️ Actions</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
      <tr style="background:#f7f8fa"><th>Action</th><th>Result</th></tr>
      <tr><td>Login</td><td>✅ Success</td></tr>
      <tr><td>Resume Upload</td><td>{"✅ Uploaded — Last Updated reset to Today" if resume_ok else "⚠️ Failed"}</td></tr>
      <tr><td>Headline Update</td><td>{"✅ Updated" if headline_ok else "⚠️ Failed"}</td></tr>
    </table>
    <h3>📊 Stats</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
      <tr style="background:#f7f8fa"><th>Metric</th><th>Value</th></tr>
      <tr><td>Profile Views</td><td>{stats.get('profile_views','N/A')}</td></tr>
      <tr><td>Resume Downloads</td><td>{stats.get('resume_downloads','N/A')}</td></tr>
    </table>
    <h3>📋 Log</h3>
    <pre style="background:#f7f8fa;padding:12px;font-size:12px;border:1px solid #e5e7eb">{"<br>".join(report)}</pre>
    <hr/>
    <p style="font-size:11px;color:#57606a;text-align:center">
      Naukri Agent &bull; Daily 9 AM IST &bull;
      <a href="https://www.naukri.com/mnjuser/profile">Open Naukri Profile</a>
    </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Naukri Agent — {run_date}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_APP_PASS)
        s.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())
    log(f"Email sent to {NOTIFY_EMAIL} ✅")

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    log("=" * 50)
    log("Naukri Profile Agent Starting")
    log("=" * 50)

    driver = make_driver()
    try:
        login(driver)
        resume_ok   = upload_resume(driver)
        headline_ok = update_headline(driver)
        stats       = fetch_stats(driver)
    finally:
        driver.quit()

    send_email(stats, resume_ok, headline_ok)
    log("=" * 50)
    log("Agent run complete ✅")
    log("=" * 50)

if __name__ == "__main__":
    main()
