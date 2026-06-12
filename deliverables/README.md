# Groww Weekly Review Pulse

This project turns recent Groww App Store and Play Store reviews into a concise weekly product pulse. It reads a reviews CSV, asks Groq's `llama-3.3-70b-versatile` model to parse the feedback using **Pydantic Structured JSON**, writes a one-page note, sends the note by email (via Resend or SMTP), and renders a rich detailed dashboard in the UI.

## What It Builds

- Imports public review exports with `rating`, `title`, `text`, and `date`.
- Clusters reviews into up to 5 themes internally.
- Outputs exactly the top 3 themes, 3 verbatim user quotes (with star ratings and dates), and 3 action ideas per theme.
- Adds a 3-line executive summary before the email body.
- Sends the note using the **Resend HTTP API** (bypassing cloud SMTP blocks) or falls back to traditional SMTP.
- Renders a massive, beautiful CSS Grid dashboard directly below the UI after generation.

## Project Files

- `pulse.py` - main backend automation script (with Pydantic schemas).
- `scrape_reviews.py` - script to scrape live App Store and Play Store reviews.
- `sample_reviews.csv` - scraped Groww review export dataset.
- `weekly_note.md` - latest generated weekly note.
- `groww-pulse-frontend/` - Flask backend and HTML/CSS/JS frontend.
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
3. Fill in `.env`:
   ```env
   Groww_weekly_review_GROQ=your_groq_key
   RESEND_API_KEY=re_your_resend_key  # Optional: For reliable email delivery
   ```

## How to Run Locally

```bash
cd groww-pulse-frontend
python app.py
```
Then visit `http://127.0.0.1:5000` to access the dashboard.

## How to Re-run for a New Week

1. Run the scraper script to fetch the latest App Store and Play Store reviews for the current week:
   ```bash
   python scrape_reviews.py
   ```
2. This will automatically filter and update `sample_reviews.csv` with fresh live data.
3. Open the web UI, enter your email, and click **Generate & Send Pulse**.
4. Scroll down to see the new **Deep Dive Dashboard** with the latest themes, quotes, and action ideas!

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
- **Customer Support** - Bot loops, ticket delays, callback quality, resolution speed

## Deployment on Railway

This project is configured to run effortlessly on Railway out of the box.

1. Create a new project on [Railway](https://railway.app/).
2. Select **Deploy from GitHub repo** and connect your `Groww-pulse` repository.
3. Go to the **Variables** tab in your Railway service and add:
   - `Groww_weekly_review_GROQ`
   - `RESEND_API_KEY` (Highly recommended, as Railway blocks outbound SMTP)
4. The included `Procfile` will automatically launch the Flask frontend using `gunicorn`. 
5. Once deployed, Railway will provide you with a public URL where you can access the frontend dashboard!
