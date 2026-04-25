import yfinance as yf
import pandas as pd
from datetime import datetime
import os

TICKERS = {
    "^NSEI":      "Nifty 50",
    "^NSEBANK":   "Nifty Bank",
    "^CNXIT":     "Nifty IT",
    "^CNXPHARMA": "Nifty Pharma",
    "^CNXAUTO":   "Nifty Auto",
    "^CNXFMCG":   "Nifty FMCG",
    "^CNXMETAL":  "Nifty Metal",
    "^CNXREALTY": "Nifty Realty",
    "^CNXENERGY": "Nifty Energy",
    "^CNXINFRA":  "Nifty Infra",
}

def fetch_sector_data(period="90d"):
    print(f"Fetching data for {len(TICKERS)} indices...")

    raw = yf.download(list(TICKERS.keys()), period=period, interval="1d")["Close"]

    # Rename columns from ticker symbols to readable names
    raw = raw.rename(columns=TICKERS)

    # Reset index so Date becomes a regular column
    raw = raw.reset_index()

    # Melt from wide format to long format
    df = raw.melt(id_vars="Date", var_name="sector", value_name="close_price")

    # Drop any rows where price is missing
    df = df.dropna(subset=["close_price"])

    # Add a fetched_at timestamp
    df["fetched_at"] = datetime.now()

    df = df.sort_values(["Date", "sector"]).reset_index(drop=True)

    print(f"Fetched {len(df)} rows")
    return df

if __name__ == "__main__":
    df = fetch_sector_data()
    print(df.head(20))
    df.to_csv("data/raw_prices.csv", index=False)
    print("Saved to data/raw_prices.csv")