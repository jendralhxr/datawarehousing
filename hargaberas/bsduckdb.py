import glob
import bs4
import duckdb
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# List of target date strings
dates = [
    "20260802",
    "20260809",
    "20260816",
    "20260823",
    "20260830",
    "20260906",
]

# Parse each HTML file into a unified Pandas DataFrame
all_frames = []

for date_str in dates:
    filename = f"{date_str}"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            soup = bs4.BeautifulSoup(f, "html.parser")

        # Extract headers and table rows
        headers = [th.get_text(strip=True) for th in soup.find_all("th")]
        rows = [
            [td.get_text(strip=True) for td in tr.find_all("td")]
            for tr in soup.find_all("tr")
            if tr.find_all("td")
        ]

        if rows:
            df = pd.DataFrame(rows, columns=headers)
            df["source_file_date"] = date_str
            all_frames.append(df)
    except FileNotFoundError:
        print(f"File {filename} not found, skipping.")

# Concatenate all tables into one unified dataset
combined_df = pd.concat(all_frames, ignore_index=True)

# Register into DuckDB for SQL querying
con = duckdb.connect()
con.register("weekly_prices", combined_df)

# Use UNPIVOT directly in DuckDB to convert dynamic date columns into rows
query = """
WITH unpivoted AS (
    UNPIVOT weekly_prices
    ON COLUMNS(* EXCLUDE (No, Lokasi, source_file_date))
    INTO
        NAME raw_tanggal
        VALUE raw_harga
)
SELECT DISTINCT
    CAST(raw_tanggal AS DATE) AS Tanggal,
    Lokasi,
    CAST(REPLACE(REPLACE(raw_harga, '.', ''), ',', '.') AS DOUBLE) AS Harga
FROM unpivoted
WHERE No = '#'
ORDER BY Tanggal ASC;
"""

df_blimbing = con.execute(query).df()
print(df_blimbing)

# Plot Time Series
plt.figure(figsize=(10, 5))
sns.lineplot(
    data=df_blimbing,
    x="Tanggal",
    y="Harga",
    marker="o",
    linewidth=2,
    color="tab:blue",
)

plt.title(
    "Price Time Series",
    fontsize=14,
    pad=15,
)
plt.xlabel("Date", fontsize=11)
plt.ylabel("Price (IDR / kg)", fontsize=11)
plt.xticks(rotation=45)
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()

plt.show()