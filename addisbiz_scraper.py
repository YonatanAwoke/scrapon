import asyncio
import sys
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import nest_asyncio
nest_asyncio.apply()

from playwright.async_api import async_playwright



import streamlit as st
import pandas as pd
import json
from io import StringIO

async def scrape_addisbiz_paginated_async(base_url, max_page, fields_to_include):
    data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for page_number in range(1, max_page + 1):
            current_url = f"{base_url}?page={page_number}"
            st.write(f"🔎 Visiting: {current_url}")
            await page.goto(current_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(6000)

            content = await page.content()
            if "No businesses found in this category" in content:
                st.warning("✅ Reached end of business listings.")
                break

            links = await page.query_selector_all('a.name')
            business_urls = [
                f"https://addisbiz.com{href}" if href.startswith("/") else href
                for link in links if (href := await link.get_attribute('href'))
            ]

            for business_url in business_urls:
                try:
                    detail_page = await context.new_page()
                    await detail_page.goto(business_url, wait_until="domcontentloaded")
                    await detail_page.wait_for_timeout(6000)

                    scripts = await detail_page.query_selector_all('script[type="application/ld+json"]')
                    for script in scripts:
                        try:
                            raw_json = await script.inner_text()
                            json_data = json.loads(raw_json)

                            if isinstance(json_data, list):
                                entries = json_data
                            else:
                                entries = [json_data]

                            found_local_business = False

                            for entry in entries:
                                if entry.get("@type") == "localBusiness":
                                    found_local_business = True
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
                                    break  # Only handle the first LocalBusiness entry

                            # if not found_local_business:
                            #     st.info(f"📄 No LocalBusiness JSON-LD found at {business_url}")
                        except json.JSONDecodeError:
                            continue
                    await detail_page.close()
                except Exception as e:
                    st.error(f"❌ Error scraping {business_url}: {e}")

        await page.close()
        await browser.close()

    return pd.DataFrame(data)

# Streamlit UI
st.set_page_config(page_title="AddisBiz Scraper", layout="centered")

st.title("🕸️ AddisBiz Business Scraper")
st.write("Scrape business listings from [AddisBiz](https://addisbiz.com).")

with st.form("scrape_form"):
    base_url = st.text_input("Enter base URL", value="https://addisbiz.com/business-directory/shopping/house-office-furniture")
    max_page = st.number_input("Number of pages to scrape", min_value=1, value=1, step=1)
    
    st.markdown("**Select fields to include:**")
    all_fields = ["name", "telephone", "faxNumber", "addressLocality", "addressRegion", "addressCountry", "url", "source_url"]
    selected_fields = st.multiselect("Fields", all_fields, default=["name", "telephone", "addressLocality", "source_url"])
    
    submitted = st.form_submit_button("Start Scraping")

if submitted:
    with st.spinner("Scraping in progress..."):
        df = asyncio.run(scrape_addisbiz_paginated_async(base_url, max_page, selected_fields))

    if not df.empty:
        st.success(f"🎉 Done! Scraped {len(df)} businesses.")

        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()

        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="addisbiz_businesses.csv",
            mime="text/csv"
        )
    else:
        st.warning("No data was scraped.")
