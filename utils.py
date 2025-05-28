import requests
import time
import streamlit as st

def fetch_with_retries(url, retries=3, delay=1):
    for _ in range(retries):
        try:
            return requests.get(url, timeout=10)
        except Exception:
            time.sleep(delay)
    return None

def parse_page_input(page_input: str):
    pages = set()
    parts = page_input.split(',')
    for part in parts:
        if '-' in part:
            try:
                start, end = map(int, part.strip().split('-'))
                pages.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                pages.add(int(part.strip()))
            except ValueError:
                continue
    return sorted(pages)
