import xarray as xr
import numpy as np
import os
import pandas as pd
from shapely.geometry import Polygon

# Define file paths
storm_data_dir = "C:/Users/abiga/OneDrive/Documents/Thesis/Year0_windfield/"  # Directory containing storm NetCDFs
lease_area_file = r"C:\Users\abiga\OneDrive\Documents\Thesis\PR_boundary.nc"  # Lease area NetCDF
output_csv = r"C:\Users\abiga\OneDrive\Documents\Thesis\storms_over_PR_year0.csv"


# Load the lease area dataset
lease_ds = xr.open_dataset(lease_area_file)
lease_mask = lease_ds["mask"]
lease_lats = lease_ds["lat"].values
lease_lons = lease_ds["lon"].values

# Convert lease area longitudes to -180 to 180 range if necessary
lease_lons = np.where(lease_lons > 180, lease_lons - 360, lease_lons)

# Define lease area polygon
lease_area_polygon = Polygon([(lease_lons.min(), lease_lats.min()),
                              (lease_lons.max(), lease_lats.min()),
                              (lease_lons.max(), lease_lats.max()),
                              (lease_lons.min(), lease_lats.max())])

# Set tolerance for longitude overlap
LON_TOLERANCE = 0.5

# Set wind speed threshold
WIND_THRESHOLD = 50

# List to store passing storm data
passing_storms_data = []

# Iterate over all storm files
storm_files = [f for f in os.listdir(storm_data_dir) if f.endswith(".nc")]
for storm_file in storm_files:
    print(f"Processing storm: {storm_file}")
    storm_path = os.path.join(storm_data_dir, storm_file)
    storm_ds = xr.open_dataset(storm_path)

    # Extract wind speed, time, and coordinates
    wind_speed = storm_ds["wind_speed"]
    time = storm_ds["time"]
    storm_lats = storm_ds["lat"].values
    storm_lons = storm_ds["lon"].values

    # Convert storm longitudes to -180 to 180 range if necessary
    storm_lons = np.where(storm_lons > 180, storm_lons - 360, storm_lons)

    # Ensure lat/lon are sorted in ascending order
    if storm_lats[0] > storm_lats[-1]:
        storm_lats = storm_lats[::-1]
        wind_speed = wind_speed.sel(lat=storm_lats)
    if storm_lons[0] > storm_lons[-1]:
        storm_lons = storm_lons[::-1]
        wind_speed = wind_speed.sel(lon=storm_lons)

    # Check if storm overlaps with lease area
    if (storm_lats.min() > lease_lats.max()) or (storm_lats.max() < lease_lats.min()):
        storm_ds.close()
        continue
    if (storm_lons.min() > lease_lons.max() + LON_TOLERANCE) or (storm_lons.max() < lease_lons.min() - LON_TOLERANCE):
        storm_ds.close()
        continue

    # Iterate over timesteps
    for t in range(len(time)):
        wind_t = wind_speed.isel(time=t).values
        
        # Create a mask to identify regions with wind speed >= threshold
        mask = wind_t >= WIND_THRESHOLD

        # Get storm footprint bounds
        if np.any(mask):
            min_lon = np.nanmin(np.where(mask, storm_lons[np.newaxis, :], np.nan))
            max_lon = np.nanmax(np.where(mask, storm_lons[np.newaxis, :], np.nan))
            min_lat = np.nanmin(np.where(mask, storm_lats[:, np.newaxis], np.nan))
            max_lat = np.nanmax(np.where(mask, storm_lats[:, np.newaxis], np.nan))

            storm_footprint_polygon = Polygon([(min_lon, min_lat),
                                               (max_lon, min_lat),
                                               (max_lon, max_lat),
                                               (min_lon, max_lat)])

            # Check intersection with lease area
            if storm_footprint_polygon.intersects(lease_area_polygon):
                passing_storms_data.append([storm_file, str(time[t].values)])

    storm_ds.close()

lease_ds.close()

# Save results to CSV
columns = ["storm_file", "time_step"]
df = pd.DataFrame(passing_storms_data, columns=columns)
df.to_csv(output_csv, index=False)

print(f"Saved {len(passing_storms_data)} storm timestep entries to {output_csv}")