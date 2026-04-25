import yfinance as yf
import pandas as pd

tickers = [
    "^NSEI",       # Nifty 50
    "^NSEBANK",    # Nifty Bank
    "^CNXIT",      # Nifty IT
    "^CNXPHARMA",  # Nifty Pharma
    "^CNXAUTO",    # Nifty Auto
    "^CNXFMCG",    # Nifty FMCG
    "^CNXMETAL",   # Nifty Metal
    "^CNXREALTY",  # Nifty Realty
    "^CNXENERGY",  # Nifty Energy
    "^CNXINFRA",   # Nifty Infra
]

data = yf.download(tickers, period="30d", interval="1d")["Close"]

print(data.tail())
print("\nShape:", data.shape)