import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from calculate import calculate_weekly_quadrants

load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="Nifty Sector Rotation Tracker",
    page_icon="📈",
    layout="wide"
)

# --- DB Connection ---
@st.cache_resource
def get_engine():
    db_url = os.getenv("DATABASE_URL")
    # Fix for SQLAlchemy compatibility
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return create_engine(db_url)

# --- Load Data ---
@st.cache_data(ttl=3600)
def load_data():
    engine = get_engine()
    df = pd.read_sql(
        "SELECT * FROM sector_calculations ORDER BY date, sector",
        engine
    )
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data()

# --- Latest snapshot ---
latest = df.sort_values("date").groupby("sector").last().reset_index()

# --- Header ---
st.title("📈 Nifty Sector Rotation Tracker")
st.caption(f"Data as of: {latest['date'].max().strftime('%d %b %Y')}")
st.markdown("---")

# --- Quadrant Summary Cards ---
st.subheader("Sector Quadrants")

col1, col2, col3, col4 = st.columns(4)

quadrant_colors = {
    "Leading":   ("🟢", col1),
    "Weakening": ("🟡", col2),
    "Improving": ("🔵", col3),
    "Lagging":   ("🔴", col4),
}

for quadrant, (emoji, col) in quadrant_colors.items():
    sectors_in_quadrant = latest[latest["quadrant"] == quadrant]["sector"].tolist()
    with col:
        st.markdown(f"**{emoji} {quadrant}**")
        if sectors_in_quadrant:
            for s in sectors_in_quadrant:
                st.markdown(f"- {s}")
        else:
            st.markdown("_None_")

st.markdown("---")

# --- Sector Rankings Table ---
st.subheader("Sector Rankings (Latest)")

table = latest[["sector", "close_price", "rs_ratio", "rs_change", "quadrant"]].copy()
table = table.sort_values("rs_ratio", ascending=False).reset_index(drop=True)
table.columns = ["Sector", "Close Price", "RS Ratio", "RS Change (5d)", "Quadrant"]
table["Close Price"] = table["Close Price"].map("{:,.0f}".format)
table["RS Ratio"] = table["RS Ratio"].map("{:.4f}".format)
table["RS Change (5d)"] = table["RS Change (5d)"].map("{:.4f}".format)

st.dataframe(table, use_container_width=True, hide_index=True)

st.markdown("---")

# --- RS Trend Chart ---
st.subheader("RS Ratio Trend (Last 90 Days)")

sectors_available = sorted(df["sector"].unique().tolist())
selected_sectors = st.multiselect(
    "Select sectors to compare:",
    options=sectors_available,
    default=["Nifty IT", "Nifty Bank", "Nifty Energy"]
)

if selected_sectors:
    filtered = df[df["sector"].isin(selected_sectors)]
    fig = px.line(
        filtered,
        x="date",
        y="rs_ratio",
        color="sector",
        title="Relative Strength vs Nifty 50 Over Time",
        labels={"rs_ratio": "RS Ratio", "date": "Date", "sector": "Sector"}
    )
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select at least one sector above to see the trend.")

st.markdown("---")

# --- Weekly Heatmap ---
st.subheader("Sector Rotation Heatmap (Last 12 Weeks)")

weekly = calculate_weekly_quadrants(df)

quadrant_map = {
    "Leading":            3,
    "Weakening":          2,
    "Improving":          1,
    "Lagging":            0,
    "Insufficient Data": -1,
}

weekly["quadrant_num"] = weekly["quadrant"].map(quadrant_map)

pivot = weekly.pivot(index="sector", columns="week_label", values="quadrant_num")

week_order = weekly.drop_duplicates("week_label").sort_values("date")["week_label"].tolist()
pivot = pivot[week_order]

colorscale = [
    [0.00, "#ef4444"],
    [0.25, "#f97316"],
    [0.50, "#3b82f6"],
    [0.75, "#facc15"],
    [1.00, "#22c55e"],
]

fig_heatmap = px.imshow(
    pivot,
    color_continuous_scale=colorscale,
    aspect="auto",
    title="Quadrant by Week (Green=Leading, Yellow=Weakening, Blue=Improving, Red=Lagging)"
)

fig_heatmap.update_coloraxes(showscale=False)
fig_heatmap.update_layout(
    xaxis_title="Week",
    yaxis_title="Sector",
    height=400
)

st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("---")
st.caption("Built with yfinance + PostgreSQL + Streamlit | Data source: Yahoo Finance")