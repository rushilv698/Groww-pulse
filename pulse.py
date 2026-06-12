import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import List

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("Groww_weekly_review_GROQ")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
REVIEW_LOOKBACK_WEEKS = int(os.getenv("REVIEW_LOOKBACK_WEEKS", "12"))


def get_llm():
    if not GROQ_API_KEY:
        raise ValueError("Missing GROQ_API_KEY in environment.")
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        groq_api_key=GROQ_API_KEY,
    )


def load_reviews(csv_path="sample_reviews.csv", lookback_weeks=REVIEW_LOOKBACK_WEEKS):
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, csv_path)
    df = pd.read_csv(csv_path)
    for col in ["rating", "title", "text", "date"]:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    if df["rating"].isna().any() or not df["rating"].between(1, 5).all():
        raise ValueError("Ratings must be numbers from 1 to 5.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        raise ValueError("One or more review dates are invalid.")

    today = pd.Timestamp.now().normalize()
    cutoff = today - pd.Timedelta(weeks=lookback_weeks)
    recent_df = df[(df["date"] >= cutoff) & (df["date"] <= today)]
    if recent_df.empty:
        raise ValueError(f"No reviews found from the last {lookback_weeks} weeks.")

    return recent_df.sort_values("date").reset_index(drop=True)


def build_reviews_text(reviews_df):
    chunks = []
    for _, row in reviews_df.iterrows():
        chunks.append(
            "\n".join(
                [
                    f"Rating: {row['rating']}",
                    f"Date: {row['date'].date()}",
                    f"Title: {row['title']}",
                    f"Review: {row['text']}",
                    "---",
                ]
            )
        )
    return "\n".join(chunks)


def select_exact_quotes(reviews_df, quote_count=3):
    selected_quotes = []
    used_themes = set()
    quote_theme_rules = [
        ("KYC/Onboarding", r"\bkyc\b|verification|document|selfie|pan|otp"),
        ("Payments/Refunds", r"upi|payment|debit|debited|refund|mandate|autopay"),
        ("Withdrawals", r"withdraw|withdrawal|redemption|redeem|payout"),
        ("App Stability", r"crash|freeze|freezes|lag|login|update|otp"),
        ("SIP/Orders", r"\bsip\b|order|stock|sell|buy|pause|cancel"),
        ("Statements/Reports", r"statement|report|capital gains|pdf|tax"),
        ("Support", r"support|ticket|agent|bot|call"),
        ("Notifications", r"notification|push|alert|reminder"),
    ]

    low_rating_reviews = reviews_df.sort_values(["rating", "date"])
    for theme_name, pattern in quote_theme_rules:
        if len(selected_quotes) == quote_count:
            break
        if theme_name in used_themes:
            continue
        matches = low_rating_reviews[
            low_rating_reviews["text"].str.contains(pattern, case=False, regex=True)
        ]
        if not matches.empty:
            selected_quotes.append(str(matches.iloc[0]["text"]))
            used_themes.add(theme_name)

    for _, row in low_rating_reviews.iterrows():
        if len(selected_quotes) == quote_count:
            break
        quote = str(row["text"])
        if quote not in selected_quotes:
            selected_quotes.append(quote)

    return selected_quotes[:quote_count]

class ReviewQuote(BaseModel):
    quote: str = Field(description="Exact verbatim quote from a user review")
    stars: int = Field(description="Star rating of the review (1-5)")
    date: str = Field(description="Date of the review in YYYY-MM-DD format")

class Theme(BaseModel):
    name: str = Field(description="Name of the theme (e.g. KYC/Onboarding)")
    volume: int = Field(description="Number of reviews in this theme")
    summary: str = Field(description="One-sentence summary of the theme")
    action_ideas: List[str] = Field(description="3 actionable ideas for the product team based on this theme")
    quotes: List[ReviewQuote] = Field(description="3 exact user quotes belonging to this theme")

class PulseReport(BaseModel):
    themes: List[Theme] = Field(description="Top 3 themes by review volume")

def format_report_to_text(report: PulseReport, date_range: str) -> str:
    lines = [f"WEEKLY GROWW PULSE\n[{date_range}]\n", "TOP THEMES"]
    for t in report.themes:
        lines.append(f"- {t.name} ({t.volume} reviews): {t.summary}")
    
    lines.append("\nQUOTES")
    quote_idx = 1
    for t in report.themes:
        for q in t.quotes:
            lines.append(f"{quote_idx}. \"{q.quote}\"")
            quote_idx += 1
            
    lines.append("\nACTION IDEAS")
    idea_idx = 1
    for t in report.themes:
        for idea in t.action_ideas:
            lines.append(f"{idea_idx}. {idea}")
            idea_idx += 1
            
    return "\n".join(lines)


def generate_weekly_note(reviews_df):
    from datetime import datetime, timedelta
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    date_range = f"{monday.date()} to {sunday.date()}"
    reviews_text = build_reviews_text(reviews_df)
    review_count = len(reviews_df)

    prompt_template = ChatPromptTemplate.from_template(
        """
You are a product analyst for the Groww app. Analyze the following recent App Store and Play Store reviews.

Rules:
- You are receiving {review_count} reviews from {date_range}.
- First cluster the reviews into up to 5 themes internally.
- Output the top 3 themes by review count.
- Use ONLY these specific 5 product themes: KYC/Onboarding, Payments/Refunds, Withdrawals, Statements/Reports, Customer Support.
- For each theme, calculate the volume of reviews that belong to it.
- For each theme, select exactly 3 distinct, real user quotes taken EXACTLY from the review text. Include their star rating and date.
- For each theme, propose exactly 3 actionable ideas the product team could implement this week.
- Do not include any personally identifiable information.
- Base the analysis only on the reviews provided.

REVIEWS:
{reviews}
"""
    )

    formatted_prompt = prompt_template.format(
        date_range=date_range,
        review_count=review_count,
        reviews=reviews_text,
    )
    
    llm = get_llm().with_structured_output(PulseReport)
    report = llm.invoke(formatted_prompt)
    
    text_note = format_report_to_text(report, date_range)
    return text_note, report


def save_weekly_note(weekly_note, opening_summary, path="weekly_note.md"):
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, path)
    with open(path, "w", encoding="utf-8") as file:
        file.write("EMAIL OPENING SUMMARY\n")
        file.write(opening_summary + "\n\n")
        file.write(weekly_note + "\n")
    print(f"Weekly note saved to {path}")


def build_email_opening(weekly_note):
    prompt_template = ChatPromptTemplate.from_template(
        """
You are writing a short email opener for a weekly Groww review pulse.

Rules:
- Write exactly 3 lines.
- Each line must be one sentence.
- Keep the tone crisp and executive-friendly.
- Summarize the main signal, the biggest user pain point, and the recommended focus this week.
- Do not repeat the full note.

WEEKLY NOTE:
{weekly_note}
"""
    )
    formatted_prompt = prompt_template.format(weekly_note=weekly_note)
    response = get_llm().invoke(formatted_prompt)
    raw_text = response.content.strip()
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if len(lines) >= 3:
        return "\n".join(lines[:3])

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", raw_text)
        if sentence.strip()
    ]
    if len(sentences) >= 3:
        return "\n".join(sentences[:3])

    while len(sentences) < 3:
        sentences.append("No additional summary line available.")
    return "\n".join(sentences[:3])


def save_draft(subject, opening_summary, weekly_note, path="draft_email.txt"):
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, path)
    with open(path, "w", encoding="utf-8") as file:
        file.write(f"Subject: {subject}\n\n{opening_summary}\n\n{weekly_note}\n")
    print(f"Draft saved to {path}")


def send_email(weekly_note, opening_summary, override_recipient=None):
    subject = "Groww Weekly Review Pulse - " + pd.Timestamp.now().strftime("%Y-%m-%d")
    body = f"""Hi,

{opening_summary}

Here is the weekly review pulse for Groww:

{weekly_note}

Generated automatically - Project prototype. No PII included.
"""

    recipient = override_recipient or RECIPIENT_EMAIL
    
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key:
        try:
            import resend
            resend.api_key = resend_key
            # Note: By default, Resend limits sending to 'onboarding@resend.dev' until you verify a domain.
            from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
            
            r = resend.Emails.send({
                "from": from_email,
                "to": recipient,
                "subject": subject,
                "text": body
            })
            print(f"Email sent successfully via Resend. ID: {r.get('id')}")
            return
        except Exception as exc:
            print(f"Failed to send email via Resend: {exc}")
            save_draft(subject, opening_summary, weekly_note)
            return

    if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, recipient]):
        print("Email credentials are incomplete. Saving a local draft instead.")
        save_draft(subject, opening_summary, weekly_note)
        return

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
        server.quit()
        print("Email sent successfully via SMTP.")
    except Exception as exc:
        print(f"Failed to send email via SMTP: {exc}")
        save_draft(subject, opening_summary, weekly_note)


def run_pulse(recipient_email=None):
    df = load_reviews()
    weekly_note, report_json = generate_weekly_note(df)
    opening_summary = build_email_opening(weekly_note)
    save_weekly_note(weekly_note, opening_summary)
    send_email(weekly_note, opening_summary, override_recipient=recipient_email)
    return weekly_note, opening_summary, len(df), report_json.model_dump()

def main():
    df = load_reviews()
    weekly_note, report_json = generate_weekly_note(df)
    opening_summary = build_email_opening(weekly_note)
    print("=== WEEKLY NOTE ===")
    print(weekly_note)
    print("\n=== EMAIL OPENING SUMMARY ===")
    print(opening_summary)
    save_weekly_note(weekly_note, opening_summary)
    print("\nSending email...")
    send_email(weekly_note, opening_summary)


if __name__ == "__main__":
    main()
