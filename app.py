import streamlit as st
import pandas as pd
import plotly.express as px
from fetch import fetch_sector_data
from calculate import run_calculations
from calculate import calculate_weekly_quadrants


# --- Page Config ---
st.set_page_config(
    page_title="Nifty Sector Rotation Tracker",
    page_icon="📈",
    layout="wide"
)

# --- Load Data ---
@st.cache_data(ttl=3600)  # Cache for 1 hour so it doesn't re-fetch on every click
def load_data():
    df = fetch_sector_data(period="90d")
    df = run_calculations(df)
    return df

df = load_data()

# --- Latest snapshot (most recent date per sector) ---
latest = df.sort_values("Date").groupby("sector").last().reset_index()

# --- Header ---
st.title("📈 Nifty Sector Rotation Tracker")
st.caption(f"Data as of: {latest['Date'].max().strftime('%d %b %Y')}")
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
    default=["Nifty IT", "Nifty Bank"]
)

if selected_sectors:
    filtered = df[df["sector"].isin(selected_sectors)]
    fig = px.line(
        filtered,
        x="Date",
        y="rs_ratio",
        color="sector",
        title="Relative Strength vs Nifty 50 Over Time",
        labels={"rs_ratio": "RS Ratio", "Date": "Date", "sector": "Sector"}
    )
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select at least one sector above to see the trend.")

st.markdown("---")




# st.markdown("---")

# --- Weekly Heatmap ---
st.subheader("Sector Rotation Heatmap (Last 12 Weeks)")

weekly = calculate_weekly_quadrants(df)

# Map quadrants to numbers for color scale
quadrant_map = {
    "Leading":            3,
    "Weakening":          2,
    "Improving":          1,
    "Lagging":            0,
    "Insufficient Data": -1,
}

weekly["quadrant_num"] = weekly["quadrant"].map(quadrant_map)

# Pivot to matrix: rows = sectors, columns = weeks
pivot = weekly.pivot(index="sector", columns="week_label", values="quadrant_num")

# Keep weeks in chronological order
week_order = weekly.drop_duplicates("week_label").sort_values("Date")["week_label"].tolist()
pivot = pivot[week_order]

# Custom color scale
colorscale = [
    [0.00, "#ef4444"],   # Lagging     - red
    [0.25, "#f97316"],   # placeholder
    [0.50, "#3b82f6"],   # Improving   - blue
    [0.75, "#facc15"],   # Weakening   - yellow
    [1.00, "#22c55e"],   # Leading     - green
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

# --- Footer ---
st.caption("Built with yfinance + Streamlit | Data source: Yahoo Finance")