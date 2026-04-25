# Nifty Sector Rotation Tracker

A data pipeline that tracks all 10 Nifty sectoral indices daily and 
classifies them into rotation quadrants based on Relative Strength analysis.

## Live Dashboard
https://nifty-sector-tracker.streamlit.app

## How It Works
- Fetches daily closing prices for 10 Nifty sector indices via yfinance
- Calculates RS Ratio (sector price / Nifty 50) and 5-day RS momentum
- Classifies each sector into: Leading, Weakening, Improving, or Lagging
- Dashboard auto-refreshes every weekday via GitHub Actions

## Tech Stack
Python, Pandas, Streamlit, Plotly, yfinance, GitHub Actions

## Run Locally
pip install -r requirements.txt
streamlit run app.py
