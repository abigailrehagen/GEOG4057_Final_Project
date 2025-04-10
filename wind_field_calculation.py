#Import libraries
import pandas as pd
import numpy as np
import netCDF4

# Load the CSV file
csv_file = r"C:\Users\abiga\OneDrive\Documents\Thesis\PR_storms\PR_storms_year7.csv"
df = pd.read_csv(csv_file, dtype={
    "P_c": np.float32,
    "V_max": np.float32,
    "R_m": np.float32,
    "latitude": np.float32,
    "longitude": np.float32,
    "unique": np.int32
})

# Set reference time
reference_time = np.datetime64("2000-01-01 00:00:00")

# Use integer time steps directly, no need for a 'datetime' column
df["time"] = df["time"].astype(np.int32)

P_AMBIENT = np.float32(1013.25)
B = np.float32(1.3)
resolution = np.float32(0.1)

# Holland wind field calculation function
def holland_wind_field(P_c, v_max, r_max, lat, lon, local_lat_range, local_lon_range, resolution=resolution):
    # Create the localized grid
    lon_grid, lat_grid = np.meshgrid(local_lon_range, local_lat_range)
    
    # Calculate distance in kilometers
    R = 111 * np.sqrt((lat_grid - lat) ** 2 + (lon_grid - lon) ** 2)
    
    # Calculate the wind speed using the Holland B model
    delta_p = P_AMBIENT - P_c
    wind_speeds = np.zeros_like(R, dtype=np.float32)
    
    valid_mask = R > 0
    wind_speeds[valid_mask] = (B * delta_p * np.exp(- (R[valid_mask] / r_max)) / np.float32(1.15) * R[valid_mask]**B) ** 0.5  
    
    # Use 0 for points outside the storm's range
    wind_speeds[~valid_mask] = 0
    
    return lon_grid, lat_grid, wind_speeds

# Process each storm separately
for unique_storm in df["unique"].unique():
    storm_df = df[df["unique"] == unique_storm]
    nc_folder = "C:/Users/abiga/OneDrive/Documents/Thesis/Year7_windfield/"
    nc_filename = nc_folder + f"storm_{unique_storm}.nc"

    # Dynamically compute latitude and longitude bounds for each storm
    min_lat = storm_df['latitude'].min() - 5
    max_lat = storm_df['latitude'].max() + 5
    latitude_extension = 0.05 * (max_lat - min_lat)
    max_lat += latitude_extension

    min_lon = storm_df['longitude'].min() - 5
    max_lon = storm_df['longitude'].max() + 5
    longitude_extension = 0.05 * (max_lon - min_lon)
    max_lon += longitude_extension

    # Create localized latitude and longitude arrays for each storm
    local_lat_range = np.arange(min_lat, max_lat, resolution)
    local_lon_range = np.arange(min_lon, max_lon, resolution)

    # Create the NetCDF file and dimensions
    with netCDF4.Dataset(nc_filename, "w") as nc:
        nc.createDimension("time", None)
        nc.createDimension("lat", len(local_lat_range))
        nc.createDimension("lon", len(local_lon_range))

        wind_speed_var = nc.createVariable("wind_speed", "i2", ("time", "lat", "lon"))
        nc.createVariable("lat", "f4", ("lat",))
        nc.variables["lat"][:] = local_lat_range
        nc.createVariable("lon", "f4", ("lon",))
        nc.variables["lon"][:] = local_lon_range
        time_var = nc.createVariable("time", "i4", ("time",))

    # For each timestep, calculate wind speeds using the localized grid
    time_index = 0
    for _, row in storm_df.iterrows():
        _, _, wind_speeds = holland_wind_field(
            np.float32(row["P_c"]),
            np.float32(row["V_max"]),
            np.float32(row["R_m"]),
            np.float32(row["latitude"]),
            np.float32(row["longitude"]),
            local_lat_range,
            local_lon_range
        )

        # Round wind speeds to the nearest integer and store as 16-bit integers
        wind_speeds_rounded = np.round(wind_speeds).astype(np.int16)

        # Append mode to add time step data into the file
        with netCDF4.Dataset(nc_filename, "a") as nc:
            nc.variables["time"][time_index] = row["time"]
            nc.variables["wind_speed"][time_index, :, :] = wind_speeds_rounded
            time_index += 1

    print(f"NetCDF file for storm {unique_storm} created successfully.")