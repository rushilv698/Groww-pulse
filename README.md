# Groww Weekly Review Pulse

This project turns recent Groww App Store and Play Store reviews into a concise weekly product pulse. It reads a reviews CSV, asks Groq's `llama-3.3-70b-versatile` model to group the feedback, writes a one-page note, and sends the note by email.

## What It Builds

- Imports public review exports with `rating`, `title`, `text`, and `date`.
- Filters reviews to the last 12 weeks by default.
- Clusters reviews into up to 5 themes internally.
- Outputs exactly the top 3 themes, 3 verbatim user quotes, and 3 action ideas.
- Adds a 3-line executive summary before the email body.
- Sends the note by SMTP, with a local `draft_email.txt` fallback.

## Project Files

- `pulse.py` - main automation script.
- `sample_reviews.csv` - sample Groww-style review export with 69 redacted reviews.
- `weekly_note.md` - latest generated weekly note.
- `draft_email.txt` - latest email draft artifact.
- `.env.example` - environment variable template.
- `requirements.txt` - Python dependencies.

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` from the example:
   ```bash
   cp .env.example .env
   ```
4. Fill in `.env`:
   ```env
   Groww_weekly_review_GROQ=your_groq_key
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SENDER_EMAIL=rushilv698@gmail.com
   SENDER_PASSWORD=your_gmail_app_password
   RECIPIENT_EMAIL=rushilv698@gmail.com
   ```

`GROQ_API_KEY` is also supported if you prefer the standard variable name.

## How to Run

```bash
python pulse.py
```

The script prints the weekly note, writes `weekly_note.md`, sends the email, and saves `draft_email.txt` if SMTP is incomplete or fails.

## How to Re-run for a New Week

1. Replace `sample_reviews.csv` with the latest public App Store and Play Store export.
2. Keep the required columns: `rating`, `title`, `text`, `date`.
3. Ensure reviews do not contain usernames, emails, phone numbers, account IDs, PAN, Aadhaar, or other PII.
4. Run `python pulse.py`.
5. Review `weekly_note.md` and confirm the email was sent.

## Output Rules

The generated note follows this structure:

- `WEEKLY GROWW PULSE`
- Date range based on imported reviews
- `TOP THEMES` with exactly 3 visible themes
- `QUOTES` with exactly 3 quotes copied from the CSV text
- `ACTION IDEAS` with exactly 3 recommended fixes

The model is instructed to cluster into 5 themes max, then show only the top 3 themes in the final note.

## Theme Legend

Possible themes based on fintech app reviews:

- **KYC/Onboarding** - Verification delays, document upload, selfie or address verification issues
- **Payments/Refunds** - UPI failures, money debited but order not placed, refund timelines
- **Withdrawals** - Redemption delays, stuck payout requests, unclear withdrawal status
- **Statements/Reports** - Confusing downloads, tax reports, missing consolidated statements
- **App Stability** - Crashes, freezes, lag, wrong NAV or portfolio display bugs
- **Support** - Bot loops, ticket delays, callback quality, resolution speed
- **SIP/Orders** - SIP pause or cancellation, order status, stock buy/sell execution
- **Notifications** - Push frequency, promotional alerts, missing critical alerts

## Privacy

PII means personally identifiable information, such as names, emails, phone numbers, user IDs, account numbers, PAN, Aadhaar, or exact addresses. This project should use only public and anonymised review text.

## Known Limits

- Theme counts are model-generated and should be spot-checked for high-stakes reporting.
- Email sending requires valid SMTP credentials and a Gmail app password when using Gmail.
- The sample CSV is synthetic but realistic; replace it with real public exports for production use.
