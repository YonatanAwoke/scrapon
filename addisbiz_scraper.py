import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
from utils import fetch_with_retries
import streamlit as st

def scrape_addisbiz_with_requests(urls, pages, fields_to_include, update_ui=None):
    data = []
    scraped_urls = set()
    business_count = 0
    estimated_total = 0

    for base_url in urls:
        for page_number in pages:
            if st.session_state.cancel_scraping:
                st.warning("🛑 Scraping canceled.")
                return pd.DataFrame(data)

            full_url = f"{base_url}?page={page_number}"
            st.write(f"🔎 Visiting: {full_url}")
            response = fetch_with_retries(full_url)
            if not response:
                st.warning(f"⚠️ Failed to fetch page {page_number}")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            if "No businesses found in this category" in soup.text:
                st.info("✅ No more businesses on this page.")
                continue

            links = soup.select("a.name")
            business_urls = [
                f"https://addisbiz.com{a['href']}" if a['href'].startswith("/") else a['href']
                for a in links if a.has_attr('href')
            ]
            business_urls = [url for url in business_urls if url not in scraped_urls]

            estimated_total += len(business_urls)

            for biz_url in business_urls:
                if st.session_state.cancel_scraping:
                    st.warning("🛑 Scraping canceled.")
                    return pd.DataFrame(data)

                scraped_urls.add(biz_url)
                detail_resp = fetch_with_retries(biz_url)
                if not detail_resp:
                    continue

                try:
                    soup = BeautifulSoup(detail_resp.content, 'html.parser')
                    scripts = soup.find_all("script", type="application/ld+json")
                    for script in scripts:
                        try:
                            json_data = json.loads(script.string)
                            entries = json_data if isinstance(json_data, list) else [json_data]

                            for entry in entries:
                                if entry.get("@type") == "localBusiness":
                                    address = entry.get("address", {})
                                    record = {
                                        key: entry.get(key, address.get(key, "")) 
                                        for key in fields_to_include if key != "source_url"
                                    }
                                    if "source_url" in fields_to_include:
                                        record["source_url"] = biz_url
                                    data.append(record)
                                    business_count += 1
                                    if update_ui:
                                        update_ui(business_count, estimated_total)
                                    break
                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    st.error(f"❌ Failed at {biz_url}: {e}")

    return pd.DataFrame(data)
