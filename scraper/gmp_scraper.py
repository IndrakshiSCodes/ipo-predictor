import time
import pandas as pd
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def clean_header(text):
    text = re.sub(r'[\n▲▼↑↓]', '', text)
    return text.strip()


def wait_for_table(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
    )
    time.sleep(2)


def scrape_current_page(driver):
    rows = []
    row_elements = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    for tr in row_elements:
        cells = tr.find_elements(By.TAG_NAME, "td")
        row_data = [td.text.strip() for td in cells]
        if row_data and any(cell != '' for cell in row_data):
            rows.append(row_data)
    return rows


def scrape_all_pages_for_year(driver, year_label):
    """Scrapes all pages for a given year after year is already selected"""
    all_rows = []
    page = 1

    while True:
        print(f"  Page {page}...", end=" ")
        rows = scrape_current_page(driver)
        all_rows.extend(rows)
        print(f"{len(rows)} rows")

        try:
            # Find active page number
            active_page = driver.find_element(By.CSS_SELECTOR, "li.page-item.active span.page-link")
            current_page_num = int(active_page.text.strip())

            # Find and click Next button
            next_btn = driver.find_element(By.XPATH,
                "//button[contains(@class,'page-link') and (contains(text(),'Next') or contains(text(),'›'))]"
            )
            parent_li = next_btn.find_element(By.XPATH, "..")
            parent_class = parent_li.get_attribute("class") or ""

            if "disabled" in parent_class:
                print(f"  Last page reached.")
                break

            next_btn.click()
            time.sleep(2)
            wait_for_table(driver)

            # Confirm page actually changed
            try:
                new_active = driver.find_element(By.CSS_SELECTOR, "li.page-item.active span.page-link")
                new_page_num = int(new_active.text.strip())
                if new_page_num == current_page_num:
                    print(f"  Page didn't change — last page.")
                    break
            except:
                pass

            page += 1

        except Exception as e:
            print(f"  Pagination ended: {e}")
            break

    return all_rows


def scrape_subscription_data():
    url = "https://www.chittorgarh.com/report/ipo_report_listing_day_gain/98/"
    years_to_scrape = ['Year 2024', 'Year 2023', 'Year 2022', 'Year 2021', 'Year 2020', 'Year 2019']

    print("Starting browser...")
    driver = get_driver()
    all_rows = []
    headers = []

    try:
        driver.get(url)
        print("Page loaded. Waiting for table...")
        wait_for_table(driver)

        # Get headers once
        header_elements = driver.find_elements(By.CSS_SELECTOR, "table thead th")
        headers = [clean_header(th.text) for th in header_elements]
        print(f"Headers: {headers}\n")

        # Find the year dropdown — first select element on page
        selects = driver.find_elements(By.TAG_NAME, "select")
        year_select = None
        for sel in selects:
            options = [o.text for o in sel.find_elements(By.TAG_NAME, "option")]
            if any("Year" in opt for opt in options):
                year_select = sel
                break

        if not year_select:
            print("Year dropdown not found. Scraping current page only.")
            all_rows = scrape_all_pages_for_year(driver, "default")
        else:
            for year_label in years_to_scrape:
                print(f"\nScraping {year_label}...")
                try:
                    Select(year_select).select_by_visible_text(year_label)
                    time.sleep(3)
                    wait_for_table(driver)
                    # Re-find select after DOM update
                    selects = driver.find_elements(By.TAG_NAME, "select")
                    for sel in selects:
                        options = [o.text for o in sel.find_elements(By.TAG_NAME, "option")]
                        if any("Year" in opt for opt in options):
                            year_select = sel
                            break
                    rows = scrape_all_pages_for_year(driver, year_label)
                    all_rows.extend(rows)
                    print(f"  Total rows so far: {len(all_rows)}")
                except Exception as e:
                    print(f"  Could not scrape {year_label}: {e}")
                    continue

        if not all_rows:
            print("No rows found.")
            return None

        max_cols = max(len(r) for r in all_rows)
        if len(headers) < max_cols:
            headers += [f"col_{i}" for i in range(len(headers), max_cols)]

        df = pd.DataFrame(all_rows, columns=headers[:max_cols])
        print(f"\nFinal shape: {df.shape}")
        return df

    except Exception as e:
        print(f"Error: {e}")
        return None

    finally:
        driver.quit()
        print("Browser closed.")


def save_subscription_raw(df, filename="subscription_raw.csv"):
    raw_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "raw", filename)
    )
    df.to_csv(raw_path, index=False)
    print(f"Saved {len(df)} rows to {raw_path}")