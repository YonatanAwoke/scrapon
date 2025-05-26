import streamlit as st
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup
from io import StringIO

def scrape_addisbiz_with_requests(base_url, max_page, fields_to_include, update_ui=None):
    data = []
    business_count = 0
    estimated_total = max_page * 52

    for page_number in range(1, max_page + 1):
        current_url = f"{base_url}?page={page_number}"
        st.write(f"🔎 Visiting: {current_url}")
        response = requests.get(current_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        if "No businesses found in this category" in soup.text:
            st.warning("✅ Reached end of business listings.")
            break

        links = soup.select('a.name')
        business_urls = [
            f"https://addisbiz.com{link['href']}" if link['href'].startswith("/") else link['href']
            for link in links if link.has_attr('href')
        ]

        for business_url in business_urls:
            try:
                detail_resp = requests.get(business_url)
                detail_soup = BeautifulSoup(detail_resp.content, 'html.parser')
                scripts = detail_soup.find_all("script", type="application/ld+json")

                for script in scripts:
                    try:
                        json_data = json.loads(script.string)
                        entries = json_data if isinstance(json_data, list) else [json_data]

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
                                business_count += 1

                                if update_ui:
                                    update_ui(business_count, estimated_total)

                                break
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                st.error(f"❌ Error scraping {business_url}: {e}")
                continue

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
    st.subheader("Progress")
    progress_bar = st.progress(0)
    count_text = st.empty()
    estimate_text = st.empty()

    def update_ui(count, estimate):
        percent_done = min(count / estimate, 1.0)
        progress_bar.progress(percent_done)
        count_text.markdown(f"**Scraped Businesses:** `{count}`")
        estimate_text.markdown(f"**Estimated Total:** ~{estimate} (based on {max_page} pages)")

    with st.spinner("Scraping in progress..."):
        df = scrape_addisbiz_with_requests(
            base_url,
            max_page,
            selected_fields,
            update_ui
        )

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
