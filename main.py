import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import json
import os
import requests
from bs4 import BeautifulSoup
import re

# --- Configuration ---
RULES_FILE = "saved_rules.json"
TARGET_METRICS = {
    "Price to Earning": ["price to earning", "p/e", "p/e ratio"],
    "Return on equity": ["return on equity", "roe"],
    "Market Capitalization": ["market cap", "market capitalization"],
    "Free cash flow 3years": ["free cash flow 3years", "fcf 3y"],
    "Dividend yield": ["dividend yield"],
    "Sales growth": ["sales growth"],
    "Net Profit latest quarter": ["net profit latest quarter", "np latest quarter"],
    "Return on capital employed": ["roce", "return on capital employed"],
    "OPM": ["opm", "operating profit margin"],
    "Profit after tax": ["pat", "profit after tax"],
    "Debt to equity": ["debt to equity", "d/e"],
    "Industry PE": ["industry pe", "industry p/e"],
    "Profit growth": ["profit growth"],
    "Free cash flow last year": ["free cash flow last year", "fcf last year"]
}
NEWS_SOURCES = {
    "Economic Times": "https://economictimes.indiatimes.com/topic/{}",
    "Mint": "https://www.livemint.com/Search/Link/Keyword/{}",
    "Business Standard": "https://www.business-standard.com/search?q={}"
}

# --- Screener Excel Parsing ---
def parse_screener_excel(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    sheets = xls.sheet_names
    found = {}
    missing = []
    company_name = "Unknown Company"

    if "Data Sheet" in sheets:
        meta = xls.parse("Data Sheet")
        first_cell = str(meta.columns[1]) if len(meta.columns) > 1 else None
        if first_cell and first_cell.strip() != "Unnamed: 1":
            company_name = first_cell.strip()

    for sheet in sheets:
        df = xls.parse(sheet)
        df = df.dropna(how='all').dropna(axis=1, how='all')

        for canonical, variants in TARGET_METRICS.items():
            if canonical in found:
                continue
            for col in df.columns:
                col_clean = str(col).lower().strip()
                if any(re.search(variant, col_clean) for variant in variants):
                    try:
                        values = df[col].dropna().values[-5:].tolist()
                        years = [f"Year {i+1}" for i in range(len(values))]
                        found[canonical] = {"years": years, "values": values}
                    except:
                        continue
            for i in range(len(df)):
                label = str(df.iloc[i, 0]).lower().strip()
                if any(any(re.search(variant, label) for variant in variants) for _ in variants):
                    try:
                        row_vals = df.iloc[i, 1:].dropna().values[-5:].tolist()
                        col_years = df.columns[1:1+len(row_vals)].astype(str).tolist()
                        found[canonical] = {"years": col_years, "values": row_vals}
                    except:
                        continue

    for key in TARGET_METRICS:
        if key not in found:
            missing.append(key)

    return company_name, found, missing
