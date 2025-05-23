import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
from io import StringIO
import streamlit as st

def get_with_retry(url, retries=3, timeout=30):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            print(f"✅ Success: {url}")
            return response
        except requests.exceptions.Timeout:
            st.warning(f"⏱️ Timeout on attempt {attempt + 1} for: {url}")
            print(f"Timeout on attempt {attempt + 1} for: {url}")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Request failed for {url}: {e}")
            print(f"Request failed for {url}: {e}")
            break
        time.sleep(2 ** attempt)
    return None

def scrape_addisbiz_paginated(base_url, max_page, fields_to_include):
    data = []

    for page_number in range(1, max_page + 1):
        current_url = f"{base_url}?page={page_number}"
        st.write(f"🔎 Visiting: {current_url}")
        print(f"🔎 Visiting: {current_url}")

        res = get_with_retry(current_url)
        if not res:
            continue

        soup = BeautifulSoup(res.text, 'html.parser')

        # Debug: print a snippet of the page
        page_text = soup.get_text()
        print("🧪 Page content preview:\n", page_text[:300])

        if "No businesses found in this category" in page_text:
            st.warning("✅ Reached end of listings.")
            print("Reached end of listings — breaking.")
            break

        business_links = soup.select("a.name")
        print(f"🔗 Found {len(business_links)} business links on page {page_number}")

        if len(business_links) == 0:
            st.warning("⚠️ No business links found. Check your selector or page layout.")
            print("⚠️ No business links found. Check selector or layout.")
            continue

        business_urls = [
            "https://addisbiz.com" + a['href'] if a['href'].startswith('/') else a['href']
            for a in business_links if a.get('href')
        ]

        for business_url in business_urls:
            print(f"➡️ Scraping detail page: {business_url}")
            detail_res = get_with_retry(business_url)
            if not detail_res:
                continue

            detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
            scripts = detail_soup.find_all("script", {"type": "application/ld+json"})
            print(f"📦 Found {len(scripts)} JSON-LD script tags")

            for script in scripts:
                try:
                    json_data = script.get_text()
                    if not json_data.strip():
                        continue

                    parsed = json.loads(json_data)
                    entries = parsed if isinstance(parsed, list) else [parsed]

                    for entry in entries:
                        if entry.get("@type") == "localBusiness":
                            address = entry.get("address", {})
                            record = {}

                            if "name" in fields_to_include:
                                record["name"] = entry.get("name")
                            if "telephone" in fields_to_include:
                                record["telephone"] = entry.get("telephone")
                            if "faxNumber" in fields_to_include:
                                record["faxNumber"] = entry.get("faxNumber")
                            if "addressLocality" in fields_to_include:
                                record["addressLocality"] = address.get("addressLocality")
                            if "addressRegion" in fields_to_include:
                                record["addressRegion"] = address.get("addressRegion")
                            if "addressCountry" in fields_to_include:
                                record["addressCountry"] = address.get("addressCountry")
                            if "url" in fields_to_include:
                                record["url"] = entry.get("url")
                            if "source_url" in fields_to_include:
                                record["source_url"] = business_url

                            data.append(record)
                            print(f"✅ Scraped: {record.get('name', 'Unnamed')}")

                            break
                        else:
                            print("ℹ️ JSON-LD entry found, but not of type 'LocalBusiness'")
                except json.JSONDecodeError as je:
                    st.warning(f"⚠️ JSON decode error at {business_url}: {je}")
                    print(f"❌ JSON decode error at {business_url}: {je}")


    return pd.DataFrame(data)

# ----------------- Streamlit UI -----------------

st.set_page_config(page_title="AddisBiz Scraper", layout="centered")
st.title("🕸️ AddisBiz Business Scraper")
st.write("Scrape business listings from [AddisBiz](https://addisbiz.com) using requests + BeautifulSoup.")

with st.form("scrape_form"):
    base_url = st.text_input("Enter base URL", value="https://addisbiz.com/business-directory/shopping/house-office-furniture")
    max_page = st.number_input("Number of pages to scrape", min_value=1, value=1, step=1)

    st.markdown("**Select fields to include:**")
    all_fields = ["name", "telephone", "faxNumber", "addressLocality", "addressRegion", "addressCountry", "url", "source_url"]
    selected_fields = st.multiselect("Fields", all_fields, default=["name", "telephone", "addressLocality", "source_url"])

    submitted = st.form_submit_button("Start Scraping")

if submitted:
    with st.spinner("Scraping in progress..."):
        df = scrape_addisbiz_paginated(base_url, max_page, selected_fields)

    if not df.empty:
        st.success(f"🎉 Done! Scraped {len(df)} businesses.")
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)

        st.download_button(
            label="📥 Download CSV",
            data=csv_buffer.getvalue(),
            file_name="addisbiz_businesses.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No data was scraped. Check logs below or try with a different URL.")
        print("❌ No data was scraped.")
