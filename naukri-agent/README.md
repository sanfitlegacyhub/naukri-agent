# Naukri Profile Agent

Automatically runs **every day at 9 AM IST** via GitHub Actions to:
- ✅ Login to Naukri
- ✅ Upload your latest resume PDF (resets "Last Updated" → boosts recruiter visibility)
- ✅ Update your profile headline + skills
- ✅ Fetch profile view stats
- ✅ Send a daily HTML email report to your Gmail

---

## Setup — One Time Only

### Step 1 — Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|---|---|
| `NAUKRI_EMAIL` | Your Naukri login email |
| `NAUKRI_PASSWORD` | Your Naukri password |
| `GMAIL_USER` | `santhoshramesh.rs@gmail.com` |
| `GMAIL_APP_PASS` | Gmail App Password (see Step 2) |
| `NOTIFY_EMAIL` | `santhoshramesh.rs@gmail.com` |

### Step 2 — Create Gmail App Password

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (if not already)
3. Go to **App Passwords** → Select app: `Mail` → Device: `Other` → name it `NaukriAgent`
4. Copy the 16-character password → paste as `GMAIL_APP_PASS` secret

### Step 3 — Add Your Resume

Place your resume PDF at:
```
resume/Santhosh_Devops_Engineer.pdf
```

### Step 4 — Push to GitHub

```bash
git add .
git commit -m "Add Naukri profile agent"
git push
```

The agent will run automatically every day at 9 AM IST.
You can also trigger it manually: **Actions → Naukri Profile Agent → Run workflow**

---

## What You Get in the Daily Email

```
Naukri Agent Report — 22 Sep 2026 09:00 AM IST
─────────────────────────────────────────────
Actions Performed
  Login               ✅ Success
  Resume Upload       ✅ Uploaded
  Profile Update      ✅ Updated

Profile Stats
  Profile Views       42
  Resume Downloads    7
  Recruiter Actions   3
─────────────────────────────────────────────
```

---

## File Structure

```
.
├── .github/
│   └── workflows/
│       └── naukri_agent.yml       # GitHub Actions schedule
├── naukri-agent/
│   ├── naukri_agent.py            # Main agent script
│   └── requirements.txt
└── resume/
    └── Santhosh_Devops_Engineer.pdf   # Your resume (add this)
```
