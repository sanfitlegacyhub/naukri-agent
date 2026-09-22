"""
Naukri Daily Resume Update Agent
- Logs into Naukri
- Uploads latest resume PDF to refresh "Last Updated" timestamp
"""

import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def get_env(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        raise ValueError(f"Missing required environment variable: {key}")
    return val


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

    if os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        opts.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts,
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def login(driver: webdriver.Chrome, email: str, password: str):
    log("Navigating to Naukri login page...")
    driver.get("https://www.naukri.com/nlogin/login")
    wait = WebDriverWait(driver, 20)

    email_field = wait.until(EC.element_to_be_clickable((By.ID, "usernameField")))
    time.sleep(1)
    email_field.click()
    email_field.clear()
    for ch in email:
        email_field.send_keys(ch)
        time.sleep(0.03)

    time.sleep(0.5)
    pass_field = wait.until(EC.element_to_be_clickable((By.ID, "passwordField")))
    pass_field.click()
    pass_field.clear()
    for ch in password:
        pass_field.send_keys(ch)
        time.sleep(0.03)

    time.sleep(1)
    # Try finding and clicking login button using multiple fallback locators
    button_xpaths = [
        "//button[@type='submit']",
        "//button[contains(@class,'login')]",
        "//button[contains(text(),'Login')]",
        "//form//button",
    ]
    login_btn = None
    for xpath in button_xpaths:
        try:
            elems = driver.find_elements(By.XPATH, xpath)
            if elems:
                login_btn = elems[0]
                break
        except Exception:
            continue

    if login_btn:
        driver.execute_script("arguments[0].click();", login_btn)
    else:
        # Fallback: Press enter on password field
        from selenium.webdriver.common.keys import Keys
        pass_field.send_keys(Keys.RETURN)

    log("Submitted login credentials.")

    # Wait for login redirect
    for _ in range(15):
        time.sleep(1)
        if "nlogin" not in driver.current_url.lower():
            break

    if "nlogin" in driver.current_url.lower():
        # Check if error message is present
        try:
            err = driver.find_element(By.XPATH, "//*[contains(@class,'server-err') or contains(@class,'error')]").text
            if err.strip():
                raise RuntimeError(f"Login failed with error: {err.strip()}")
        except Exception as e:
            if "Login failed with error" in str(e):
                raise
        raise RuntimeError("Login failed: Still on login page after submission.")
    log("Logged in successfully.")


def upload_resume(driver: webdriver.Chrome, resume_path: str):
    if not os.path.isfile(resume_path):
        raise FileNotFoundError(f"Resume file not found at: {resume_path}")

    log(f"Navigating to profile page for resume upload...")
    driver.get("https://www.naukri.com/mnjuser/profile")
    time.sleep(3)

    wait = WebDriverWait(driver, 20)
    upload_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
    upload_input.send_keys(resume_path)
    time.sleep(5)
    log(f"Resume uploaded successfully from {resume_path}")


def main():
    email = get_env("NAUKRI_EMAIL")
    password = get_env("NAUKRI_PASSWORD")

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resume_path = os.environ.get(
        "RESUME_PATH",
        os.path.join(repo_root, "resume", "Santhosh_Devops_Engineer.pdf")
    )
    if not os.path.isabs(resume_path):
        resume_path = os.path.join(repo_root, resume_path)

    log("=" * 45)
    log("Starting Daily Resume Update Agent")
    log(f"Resume: {resume_path}")
    log("=" * 45)

    driver = make_driver()
    try:
        login(driver, email, password)
        upload_resume(driver, resume_path)
        log("Daily resume update completed successfully.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
