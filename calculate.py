import pandas as pd

def calculate_rs(df):
    # Separate Nifty 50 (our benchmark) from sectors
    nifty = df[df["sector"] == "Nifty 50"][["Date", "close_price"]].copy()
    nifty = nifty.rename(columns={"close_price": "nifty_close"})

    sectors = df[df["sector"] != "Nifty 50"].copy()

    # Merge each sector row with the Nifty 50 price on the same date
    merged = sectors.merge(nifty, on="Date", how="left")

    # RS Ratio = sector price / nifty price
    merged["rs_ratio"] = merged["close_price"] / merged["nifty_close"]

    return merged

def calculate_rs_change(df):
    # Sort so we can compare today vs 5 days ago
    df = df.sort_values(["sector", "Date"]).copy()

    # RS 5 days ago for the same sector
    df["rs_ratio_5d_ago"] = df.groupby("sector")["rs_ratio"].shift(5)

    # RS Change = is RS higher or lower than 5 days ago?
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

if __name__ == "__main__":
    df = pd.read_csv("data/raw_prices.csv", parse_dates=["Date"])
    
    result = run_calculations(df)
    
    # Show only the latest date for each sector
    latest = result.sort_values("Date").groupby("sector").last().reset_index()
    
    cols = ["sector", "close_price", "rs_ratio", "rs_change", "quadrant"]
    print(latest[cols].to_string(index=False))
    
    result.to_csv("data/calculated.csv", index=False)
    print("\nSaved to data/calculated.csv")