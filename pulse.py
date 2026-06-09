import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

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


def enforce_exact_quotes(weekly_note, reviews_df):
    quotes = select_exact_quotes(reviews_df)
    quotes_block = "QUOTES\n" + "\n".join(
        f'{index}. "{quote}"' for index, quote in enumerate(quotes, start=1)
    )
    return re.sub(
        r"QUOTES\n(?:\d+\.\s+\".*?\"\n?){1,3}",
        quotes_block + "\n",
        weekly_note,
        flags=re.DOTALL,
    ).strip()


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
- In the final note, show exactly the top 3 themes by review count.
- Do not show Theme 4 or Theme 5 in the final note.
- If the review volume is small, use fewer than 5 themes rather than inventing extra categories.
- Use ONLY these specific 5 product themes: KYC/Onboarding, Payments/Refunds, Withdrawals, Statements/Reports.
- Do not use broad umbrella themes such as Technical Issues, User Experience, or General Feedback.
- For each theme, include the count of reviews that belong to it.
- Select three distinct, real user quotes taken exactly from the review text.
- Propose three actionable ideas the product team could implement this week.
- Keep the entire note under 250 words.
- Do not include any personally identifiable information.
- Preserve the output format exactly.
- Base the analysis only on the reviews provided.

Output format:
WEEKLY GROWW PULSE
[{date_range}]

TOP THEMES
- Theme Name (X reviews): one-sentence summary
- Theme Name (X reviews): one-sentence summary
- Theme Name (X reviews): one-sentence summary

QUOTES
1. "Exact user quote 1"
2. "Exact user quote 2"
3. "Exact user quote 3"

ACTION IDEAS
1. Action item 1
2. Action item 2
3. Action item 3

REVIEWS:
{reviews}
"""
    )

    formatted_prompt = prompt_template.format(
        date_range=date_range,
        review_count=review_count,
        reviews=reviews_text,
    )
    response = get_llm().invoke(formatted_prompt)
    return enforce_exact_quotes(response.content.strip(), reviews_df)


def save_weekly_note(weekly_note, opening_summary, path="weekly_note.md"):
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
    with open(path, "w", encoding="utf-8") as file:
        file.write(f"Subject: {subject}\n\n{opening_summary}\n\n{weekly_note}\n")
    print(f"Draft saved to {path}")


def send_email(weekly_note, opening_summary, override_recipient=None):
    subject = "Groww Weekly Review Pulse - " + pd.Timestamp.now().strftime("%Y-%m-%d")
    body = f"""
    <p>Hi,</p>
    <p>{opening_summary.replace(chr(10), '<br>')}</p>
    <p>Here is the weekly review pulse for Groww:</p>
    <pre>{weekly_note}</pre>
    <p><i>Generated automatically - Project prototype. No PII included.</i></p>
    """

    recipient = override_recipient or RECIPIENT_EMAIL
    if not all([SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, recipient]):
        print("Email credentials are incomplete. Saving a local draft instead.")
        save_draft(subject, opening_summary, weekly_note)
        return

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
        server.quit()
        print("Email sent successfully.")
    except Exception as exc:
        print(f"Failed to send email: {exc}")
        save_draft(subject, opening_summary, weekly_note)


def run_pulse(recipient_email=None):
    df = load_reviews()
    weekly_note = generate_weekly_note(df)
    opening_summary = build_email_opening(weekly_note)
    save_weekly_note(weekly_note, opening_summary)
    send_email(weekly_note, opening_summary, override_recipient=recipient_email)
    return weekly_note, opening_summary, len(df)


def main():
    df = load_reviews()
    weekly_note = generate_weekly_note(df)
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
