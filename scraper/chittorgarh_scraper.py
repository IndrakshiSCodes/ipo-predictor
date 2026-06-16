import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

YEARS = [2020, 2021, 2022, 2023, 2024]  # Add more years later if needed

def scrape_ipo_data():
    """
    Scrapes historical IPO listing performance from ipocentral.in.
    Collects data across multiple years and returns one combined DataFrame.
    """
    url = "https://ipocentral.in/past-recent-ipos/"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

    soup = BeautifulSoup(response.text, "lxml")
    tables = soup.find_all("table")
    print(f"Found {len(tables)} table(s) on page")

    all_dfs = []

    for table in tables:
        rows = []
        all_rows = table.find_all("tr")

        if not all_rows:
            continue

        headers = [th.get_text(strip=True) for th in all_rows[0].find_all(["th", "td"])]

        for tr in all_rows[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)

        if rows and headers:
            max_cols = max(len(r) for r in rows)
            if len(headers) < max_cols:
                headers += [f"col_{i}" for i in range(len(headers), max_cols)]
            df = pd.DataFrame(rows, columns=headers[:max_cols])
            all_dfs.append(df)

    if not all_dfs:
        print("No tables parsed.")
        return None

    # Combine all year tables into one
    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"Total rows collected: {len(combined)}")
    return combined


def save_raw(df, filename="ipo_raw.csv"):
    raw_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "raw", filename)
    )
    df.to_csv(raw_path, index=False)
    print(f"Saved {len(df)} rows to {raw_path}")