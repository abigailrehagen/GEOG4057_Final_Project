#Import libraries
import pandas as pd
import numpy as np

# Load the storm CSV
csv_file = r"C:\Users\abiga\OneDrive\Documents\Thesis\PR_storms\PR_storms_year0.csv"
df = pd.read_csv(csv_file, dtype={
    "P_c": np.float32,
    "V_max": np.float32,
    "R_m": np.float32,
    "latitude": np.float32,
    "longitude": np.float32,
    "unique": np.int32
})
df["time"] = df["time"].astype(np.int32)

# Constants
P_AMBIENT = np.float32(1013.25)
B = np.float32(1.3)
resolution = np.float32(0.1)

# Holland wind field function
def holland_wind_field(P_c, v_max, r_max, lat, lon, local_lat_range, local_lon_range):
    lon_grid, lat_grid = np.meshgrid(local_lon_range, local_lat_range)
    R = 111 * np.sqrt((lat_grid - lat) ** 2 + (lon_grid - lon) ** 2)
    delta_p = P_AMBIENT - P_c
    wind_speeds = np.zeros_like(R, dtype=np.float32)
    valid_mask = R > 0
    wind_speeds[valid_mask] = (B * delta_p * np.exp(- (R[valid_mask] / r_max)) / 1.15 * R[valid_mask]**B) ** 0.5
    return wind_speeds

# Filter to storm 1005
storm_id = 1005
storm_df = df[df["unique"] == storm_id]

if storm_df.empty:
    raise ValueError(f"No data found for storm with unique == {storm_id}")

# Determine grid bounds
min_lat = storm_df['latitude'].min() - 5
max_lat = storm_df['latitude'].max() + 5
max_lat += 0.05 * (max_lat - min_lat)

min_lon = storm_df['longitude'].min() - 5
max_lon = storm_df['longitude'].max() + 5
max_lon += 0.05 * (max_lon - min_lon)

local_lat_range = np.arange(min_lat, max_lat, resolution)
local_lon_range = np.arange(min_lon, max_lon, resolution)

# Collect wind speed data into rows (filtering speeds < 17)
csv_rows = []
for idx, row in storm_df.iterrows():
    print(f"Processing time step {idx+1} of {len(storm_df)} (time={row['time']})")

    wind_speeds = holland_wind_field(
        row["P_c"],
        row["V_max"],
        row["R_m"],
        row["latitude"],
        row["longitude"],
        local_lat_range,
        local_lon_range
    )
    wind_speeds_rounded = np.round(wind_speeds).astype(np.int16)

    for lat_idx, lat in enumerate(local_lat_range):
        for lon_idx, lon in enumerate(local_lon_range):
            wind_speed = wind_speeds_rounded[lat_idx, lon_idx]
            if wind_speed >= 17:
                csv_rows.append([row["time"], lat, lon, wind_speed])

# Save to CSV
csv_df = pd.DataFrame(csv_rows, columns=["time", "latitude", "longitude", "wind_speed"])
output_path = rf"C:\Users\abiga\OneDrive\Documents\Thesis\storm_{storm_id}_windfield.csv"
csv_df.to_csv(output_path, index=False)

print(f"CSV saved to {output_path}")