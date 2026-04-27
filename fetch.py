import yfinance as yf
import pandas as pd
from datetime import datetime
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

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

def get_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not set in .env")
    return create_engine(db_url)

def create_tables(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sector_prices (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                sector VARCHAR(50) NOT NULL,
                close_price FLOAT NOT NULL,
                fetched_at TIMESTAMP NOT NULL,
                UNIQUE(date, sector)
            )
        """))
        conn.commit()
    print("Tables ready")

def fetch_sector_data(period="90d"):
    print(f"Fetching data for {len(TICKERS)} indices...")

    try:
        raw = yf.download(list(TICKERS.keys()), period=period, interval="1d")["Close"]
    except Exception as e:
        print(f"ERROR: yfinance fetch failed — {e}")
        raise

    raw = raw.rename(columns=TICKERS)
    raw = raw.reset_index()
    df = raw.melt(id_vars="Date", var_name="sector", value_name="close_price")
    df = df.dropna(subset=["close_price"])
    df["fetched_at"] = datetime.now()
    df = df.sort_values(["Date", "sector"]).reset_index(drop=True)

    print(f"Fetched {len(df)} rows")
    return df
def save_to_db(df, engine):
    df = df.rename(columns={"Date": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.date

    try:
        df.to_sql(
            "sector_prices",
            engine,
            if_exists="append",
            index=False,
            method="multi"
        )
        print(f"Saved {len(df)} rows")
    except Exception as e:
        # Bulk insert failed likely due to duplicates — fall back to upsert
        print(f"Bulk insert failed, trying upsert — {e}")
        with engine.connect() as conn:
            for _, row in df.iterrows():
                try:
                    conn.execute(text("""
                        INSERT INTO sector_prices (date, sector, close_price, fetched_at)
                        VALUES (:date, :sector, :close_price, :fetched_at)
                        ON CONFLICT (date, sector) DO NOTHING
                    """), {
                        "date": row["date"],
                        "sector": row["sector"],
                        "close_price": row["close_price"],
                        "fetched_at": row["fetched_at"]
                    })
                except Exception as row_error:
                    print(f"WARNING: skipped {row['sector']} {row['date']} — {row_error}")
            conn.commit()
        print("Upsert complete")
        
if __name__ == "__main__":
    engine = get_engine()
    create_tables(engine)
    df = fetch_sector_data()
    save_to_db(df, engine)
    print("Done")