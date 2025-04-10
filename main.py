import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
import requests
from bs4 import BeautifulSoup
import easyocr
from PIL import Image
import tempfile
import re

# ---------------------- CONFIG ----------------------
REQUIRED_METRICS = {
    "Current Price": "CMP Rs.",
    "Price to Earning": "P/E",
    "Market Capitalization": "Mar Cap Rs.Cr.",
    "Dividend Yield": "Div Yld %",
    "Return on Capital Employed": "ROCE %",
    "Operating Profit Margin": "OPM %",
    "Profit After Tax": "PAT 12M Rs.Cr.",
    "Debt to Equity": "Debt / Eq",
    "Return on Equity": "ROE %",
    "Sales Growth": "Sales growth %",
    "Industry PE": "Ind PE",
    "Profit Growth": "Profit growth %"
}

NEWS_SOURCES = {
    "Economic Times": "https://economictimes.indiatimes.com/topic/{}",
    "Mint": "https://www.livemint.com/Search/Link/Keyword/{}",
    "Business Standard": "https://www.business-standard.com/search?q={}"
}

# ---------------------- OCR UTILS ----------------------
def extract_from_image(uploaded_image):
    reader = easyocr.Reader(['en'], gpu=False)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        image = Image.open(uploaded_image)
        image.save(tmp_file.name)
        result = reader.readtext(tmp_file.name, detail=0, paragraph=True)
    text = " ".join(result)
    return text

# ---------------------- EVALUATION ----------------------
def evaluate_rule(val, rule):
    try:
        op = rule.strip()[0:2] if rule[1] in '=<' else rule[0]
        num = float(rule.replace(op, ''))
        return eval(f"{val} {op} {num}")
    except:
        return False

def evaluate_all(metrics, rules):
    results = []
    for metric, rule in rules.items():
        value = metrics.get(metric)
        if value is None:
            results.append((metric, "Missing", rule, False))
            continue
        try:
            val = float(value)
            passed = evaluate_rule(val, rule)
            results.append((metric, val, rule, passed))
        except:
            results.append((metric, value, rule, False))
    return results

# ---------------------- NEWS ----------------------
def fetch_news(company):
    st.subheader(f"📰 News & Sentiment: {company}")
    for name, url in NEWS_SOURCES.items():
        st.markdown(f"**{name}**")
        try:
            r = requests.get(url.format(company.replace(" ", "+")), headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(r.content, 'html.parser')
            links = [a for a in soup.find_all('a', href=True) if len(a.text.strip()) > 30 and company.split()[0].lower() in a.text.lower()]
            for link in links[:5]:
                st.markdown(f"- [{link.text.strip()}]({link['href']})")
        except:
            st.warning(f"Could not fetch news from {name}")

# ---------------------- STREAMLIT APP ----------------------
st.set_page_config("Stock Evaluation Tool", layout="wide")
st.title("📊 In-Depth Stock Analysis (India) — Peer Comparison Based")

# Company name input
company_name = st.text_input("🏷️ Company Name (for news fetch)", "")

# Manual entry layout
st.subheader("📥 Manually Enter Financial Metrics")
manual_inputs = {}
cols = st.columns(3)
for idx, (label, _) in enumerate(REQUIRED_METRICS.items()):
    val = cols[idx % 3].text_input(f"{label}", key=f"manual_{label}")
    if val:
        manual_inputs[label] = val

# OCR from image
st.markdown("---")
st.subheader("📸 Upload Screenshot of Peer Comparison Table")
uploaded_image = st.file_uploader("Upload screenshot (PNG/JPG)", type=["png", "jpg", "jpeg"])
ocr_data = {}
if uploaded_image:
    with st.spinner("🔍 Extracting text from image..."):
        raw_text = extract_from_image(uploaded_image)
        for label, abbrev in REQUIRED_METRICS.items():
            for line in raw_text.split(" "):
                if abbrev.lower() in line.lower():
                    try:
                        value = re.findall(r"\d+\.\d+|\d+", line)
                        if value:
                            ocr_data[label] = value[0]
                    except:
                        continue

# Merge manual with OCR (OCR takes precedence)
metrics = manual_inputs.copy()
metrics.update(ocr_data)

# Rule input section
st.markdown("---")
st.subheader("⚙️ Set Evaluation Criteria")
rules = {}
cols = st.columns(3)
for idx, label in enumerate(REQUIRED_METRICS):
    rule_val = cols[idx % 3].text_input(f"{label} Rule", key=f"rule_{label}", value="")
    if rule_val:
        rules[label] = rule_val

# Evaluate button
st.markdown("---")
if st.button("✅ Evaluate"):
    if len(metrics) < len(REQUIRED_METRICS):
        missing = [k for k in REQUIRED_METRICS if k not in metrics]
        st.error(f"❌ Missing data for: {', '.join(missing)}")
    else:
        st.success("All required metrics available. Proceeding with evaluation.")

        st.subheader("📈 Evaluation Results")
        results = evaluate_all(metrics, rules)
        score = int(100 * sum(r[3] for r in results) / len(results)) if results else 0
        st.markdown(f"### ✅ Match Score: **{score}%**")
        for metric, value, rule, passed in results:
            icon = "✅" if passed else "❌"
            st.write(f"{icon} {metric}: {value} (Rule: {rule})")

        if company_name:
            st.markdown("---")
            fetch_news(company_name)
        else:
            st.info("📌 Enter a company name above to fetch related news.")
