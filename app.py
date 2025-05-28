import streamlit as st
import pandas as pd
from io import StringIO
from addisbiz_scraper import scrape_addisbiz_with_requests
from utils import parse_page_input

# Session state
if "cancel_scraping" not in st.session_state:
    st.session_state.cancel_scraping = False

st.set_page_config(page_title="AddisBiz Scraper", layout="centered")
st.title("🕸️ AddisBiz Business Scraper")
st.write("Scrape business listings from [AddisBiz](https://addisbiz.com).")

with st.form("scrape_form"):
    urls_input = st.text_area("Enter one or more category URLs (one per line)", value="https://addisbiz.com/business-directory/shopping/house-office-furniture")
    page_input = st.text_input("Enter page numbers (e.g., `1,4,6` or `1-3`)", value="1-2")

    st.markdown("**Select fields to include:**")
    all_fields = ["name", "telephone", "faxNumber", "addressLocality", "addressRegion", "addressCountry", "url", "source_url"]
    selected_fields = st.multiselect("Fields", all_fields, default=["name", "telephone", "addressLocality", "source_url"])
    
    submitted = st.form_submit_button("Start Scraping")

if submitted:
    urls = [url.strip() for url in urls_input.strip().splitlines() if url.strip()]
    pages = parse_page_input(page_input)

    st.session_state.cancel_scraping = False
    cancel_button = st.button("❌ Cancel Scraping")
    progress_bar = st.progress(0)
    count_text = st.empty()
    estimate_text = st.empty()

    def update_ui(current_count, estimated_count):
        progress_bar.progress(min(current_count / max(estimated_count, 1), 1.0))
        count_text.markdown(f"**Scraped Businesses:** `{current_count}`")
        estimate_text.markdown(f"**Estimated Total:** ~{estimated_count}")

    with st.spinner("Scraping in progress..."):
        df = scrape_addisbiz_with_requests(urls, pages, selected_fields, update_ui)

    if not st.session_state.cancel_scraping:
        if not df.empty:
            st.success(f"🎉 Done! Scraped {len(df)} businesses.")
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            st.download_button("📥 Download CSV", csv_buffer.getvalue(), "addisbiz_businesses.csv", "text/csv")
        else:
            st.warning("No data was scraped.")
