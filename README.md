# Naukri Daily Resume Update Agent

An automated agent that runs daily at 9:00 AM IST to upload your latest resume to Naukri, keeping your "Last Updated" timestamp fresh to boost recruiter visibility.

## Setup

### GitHub Secrets
Configure the following secrets under **Settings > Secrets and variables > Actions**:

- `NAUKRI_EMAIL`: Your Naukri account email
- `NAUKRI_PASSWORD`: Your Naukri account password

### Resume File
Place your resume PDF at:
```
resume/Santhosh_Devops_Engineer.pdf
```

## Running Manually
Trigger anytime via **Actions > Naukri Daily Resume Update > Run workflow**.
