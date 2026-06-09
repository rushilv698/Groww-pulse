import os
import pandas as pd
from datetime import datetime, timedelta
from google_play_scraper import Sort, reviews as play_reviews
from app_store_scraper import AppStore

CSV_FILE = "sample_reviews.csv"

def get_current_week_bounds():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday

def scrape_play_store(start_date):
    print("Scraping Google Play Store...")
    try:
        # Fetch up to 2000 newest reviews to ensure we cover the week
        result, _ = play_reviews(
            'com.nextbillion.groww',
            lang='en',
            country='in',
            sort=Sort.NEWEST,
            count=2000
        )
        parsed = []
        for r in result:
            review_date = r['at']
            if review_date >= start_date:
                parsed.append({
                    "rating": r['score'],
                    "title": "", # Play store often lacks a distinct title
                    "text": str(r.get('content', '')).replace('\n', ' ').strip(),
                    "date": review_date
                })
        print(f"  Found {len(parsed)} Play Store reviews for this week.")
        return parsed
    except Exception as e:
        print(f"Error scraping Play Store: {e}")
        return []

def scrape_app_store(start_date):
    print("Scraping Apple App Store...")
    try:
        app = AppStore(country='in', app_name='groww', app_id='1404122193')
        app.review(how_many=2000)
        parsed = []
        for r in app.reviews:
            review_date = r['date']
            if review_date >= start_date:
                parsed.append({
                    "rating": r['rating'],
                    "title": str(r.get('title', '')).replace('\n', ' ').strip(),
                    "text": str(r.get('review', '')).replace('\n', ' ').strip(),
                    "date": review_date
                })
        print(f"  Found {len(parsed)} App Store reviews for this week.")
        return parsed
    except Exception as e:
        print(f"Error scraping App Store: {e}")
        return []

def main():
    monday, sunday = get_current_week_bounds()
    print(f"Current week: {monday.date()} to {sunday.date()}")

    new_reviews = []
    new_reviews.extend(scrape_play_store(monday))
    new_reviews.extend(scrape_app_store(monday))

    new_df = pd.DataFrame(new_reviews)
    if new_df.empty:
        print("No new reviews found for this week yet.")
        return

    # Ensure date is datetime
    new_df['date'] = pd.to_datetime(new_df['date'])

    # Determine append or overwrite
    append = False
    if os.path.exists(CSV_FILE):
        try:
            existing_df = pd.read_csv(CSV_FILE)
            existing_df['date'] = pd.to_datetime(existing_df['date'], errors='coerce')
            
            # If the CSV is not empty, check the most recent review date
            if not existing_df.empty:
                max_date = existing_df['date'].max()
                if pd.notna(max_date) and max_date >= monday:
                    append = True
        except Exception as e:
            print(f"Error reading existing CSV, will overwrite: {e}")

    if append:
        print(f"Existing reviews belong to the current week. Appending to {CSV_FILE}...")
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        # Drop duplicates based on the text to avoid double counting
        combined_df = combined_df.drop_duplicates(subset=['text'], keep='last')
    else:
        print(f"New week detected! Overwriting {CSV_FILE} with fresh data...")
        combined_df = new_df

    # Sort by date descending
    combined_df = combined_df.sort_values(by='date', ascending=False)
    
    # Filter reviews to only keep those related to the 5 requested themes:
    # Onboarding, KYC, Payments, Statements, Withdrawals
    theme_pattern = r"(?i)\b(onboarding|kyc|verification|document|pan|payment|payments|upi|debit|debited|refund|statement|statements|report|tax|withdraw|withdrawal|withdrawals|redemption|redeem|payout)\b"
    
    initial_count = len(combined_df)
    combined_df = combined_df[combined_df['text'].str.contains(theme_pattern, na=False)]
    
    print(f"Filtered out {initial_count - len(combined_df)} reviews that did not match the 5 target themes.")

    # Save to CSV
    combined_df[['rating', 'title', 'text', 'date']].to_csv(CSV_FILE, index=False)
    print(f"Done. Total reviews saved: {len(combined_df)}")

if __name__ == "__main__":
    main()
