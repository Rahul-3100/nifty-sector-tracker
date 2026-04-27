import pandas as pd
from datetime import datetime
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

@st.cache_resource
def get_engine():
    db_url = os.getenv("DATABASE_URL")
    # Fix for SQLAlchemy compatibility
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return create_engine(db_url)

def create_calculations_table(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sector_calculations (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                sector VARCHAR(50) NOT NULL,
                close_price FLOAT,
                rs_ratio FLOAT,
                rs_change FLOAT,
                quadrant VARCHAR(30),
                calculated_at TIMESTAMP,
                UNIQUE(date, sector)
            )
        """))
        conn.commit()
    print("Calculations table ready")

def load_from_db(engine):
    df = pd.read_sql("SELECT * FROM sector_prices ORDER BY date, sector", engine)
    df["date"] = pd.to_datetime(df["date"])
    return df

def calculate_rs(df):
    nifty = df[df["sector"] == "Nifty 50"][["date", "close_price"]].copy()
    nifty = nifty.rename(columns={"close_price": "nifty_close"})
    sectors = df[df["sector"] != "Nifty 50"].copy()
    merged = sectors.merge(nifty, on="date", how="left")
    merged["rs_ratio"] = merged["close_price"] / merged["nifty_close"]
    return merged

def calculate_rs_change(df):
    df = df.sort_values(["sector", "date"]).copy()
    df["rs_ratio_5d_ago"] = df.groupby("sector")["rs_ratio"].shift(5)
    df["rs_change"] = df["rs_ratio"] - df["rs_ratio_5d_ago"]
    return df

def classify_quadrant(row):
    if pd.isna(row["rs_change"]):
        return "Insufficient Data"
    if row["rs_ratio"] >= 1 and row["rs_change"] >= 0:
        return "Leading"
    elif row["rs_ratio"] >= 1 and row["rs_change"] < 0:
        return "Weakening"
    elif row["rs_ratio"] < 1 and row["rs_change"] >= 0:
        return "Improving"
    else:
        return "Lagging"

def run_calculations(df):
    df = calculate_rs(df)
    df = calculate_rs_change(df)
    df["quadrant"] = df.apply(classify_quadrant, axis=1)
    return df

def save_calculations_to_db(df, engine):
    df["calculated_at"] = datetime.now()
    cols = ["date", "sector", "close_price", "rs_ratio", "rs_change", "quadrant", "calculated_at"]
    df = df[cols].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date

    with engine.connect() as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(text("""
                    INSERT INTO sector_calculations 
                        (date, sector, close_price, rs_ratio, rs_change, quadrant, calculated_at)
                    VALUES 
                        (:date, :sector, :close_price, :rs_ratio, :rs_change, :quadrant, :calculated_at)
                    ON CONFLICT (date, sector) DO UPDATE SET
                        rs_ratio = EXCLUDED.rs_ratio,
                        rs_change = EXCLUDED.rs_change,
                        quadrant = EXCLUDED.quadrant,
                        calculated_at = EXCLUDED.calculated_at
                """), row.to_dict())
            except Exception as e:
                print(f"WARNING: skipped {row['sector']} {row['date']} — {e}")
        conn.commit()

    print(f"Saved {len(df)} calculation rows")

def calculate_weekly_quadrants(df):
    sectors = df[df["sector"] != "Nifty 50"].copy()
    sectors["date"] = pd.to_datetime(sectors["date"])

    # Pivot to wide, resample, then melt back
    wide = sectors.pivot(index="date", columns="sector", values="quadrant")
    weekly = wide.resample("W").last()

    # Back to long format
    weekly = weekly.reset_index().melt(id_vars="date", var_name="sector", value_name="quadrant")
    weekly = weekly.dropna(subset=["quadrant"])

    # Keep last 12 weeks
    last_12_weeks = sorted(weekly["date"].unique())[-12:]
    weekly = weekly[weekly["date"].isin(last_12_weeks)]

    weekly["week_label"] = weekly["date"].dt.strftime("%b %d")

    return weekly[["sector", "date", "week_label", "quadrant"]]

if __name__ == "__main__":
    engine = get_engine()
    create_calculations_table(engine)
    df = load_from_db(engine)
    result = run_calculations(df)
    save_calculations_to_db(result, engine)

    latest = result.sort_values("date").groupby("sector").last().reset_index()
    cols = ["sector", "close_price", "rs_ratio", "rs_change", "quadrant"]
    print(latest[cols].to_string(index=False))
    print("Done")