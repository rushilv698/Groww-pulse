# Groww Weekly Review Pulse

An automated pipeline that takes App Store and Play Store reviews from the last 8–12 weeks, groups them into themes, and generates a one-page weekly note plus an email draft.

## Setup

1. Create a virtual environment if you want:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your credentials.

## How to Re-run for a New Week

1. Replace `sample_reviews.csv` with the latest export of public reviews.
2. Ensure the CSV has columns: `rating`, `title`, `text`, `date`.
3. Run `python pulse.py`.
4. The weekly note prints to the console and an email is sent, or a draft is saved locally.

## Theme Legend

Possible themes based on fintech app reviews:

- **KYC/Onboarding** – Verification delays, video KYC issues
- **Payments** – UPI failures, money debited but order not placed
- **Withdrawals** – Delays, stuck requests
- **Statements** – Confusing downloads, missing consolidated statements
- **App Stability** – Crashes, freezes, wrong NAV or UI bugs
- **Customer Support** – Response time, quality
- **SIP/Orders** – Pause, stop, execution issues
- **Notifications** – Frequency, relevance

The LLM dynamically selects up to 5 themes per run based on review content.

## Known Limits

- The LLM may occasionally miscount theme reviews; spot-check for consistency.
- Email sending requires a valid SMTP configuration.
- No PII is stored or processed; all reviews in the CSV should be anonymised.
