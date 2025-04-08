import arcpy
import os
import pandas as pd

def script_tool(csv_path, buffer_shapefile, output_csv_path):
    """Script tool to process storm data from CSV and export a joined table as CSV."""

    # Extract folder and file name from the path
    output_folder = os.path.dirname(output_csv_path)
    output_csv_name = os.path.basename(output_csv_path)

    # Temporary names
    points_layer = "all_data_year0"
    line_layer = "all_data_year0_line"
    selected_lines = "PR_storms_year0"

    # Step 1: Create points from CSV
    arcpy.management.XYTableToPoint(
        csv_path, points_layer, "Longitude", "Latitude",  # Make sure field names match your CSV
        coordinate_system=arcpy.SpatialReference(4326)
    )

    # Step 2: Add unique ID field
    arcpy.management.AddField(points_layer, "unique", "DOUBLE")
    arcpy.management.CalculateField(points_layer, "unique", "(!YEAR! * 100) + !TC_NUMBER!", "PYTHON3")

    # Step 3: Convert points to line
    arcpy.management.PointsToLine(points_layer, line_layer, Line_Field="unique", Sort_Field="time")

    # Step 4: Select lines that intersect the buffer shapefile
    arcpy.management.MakeFeatureLayer(line_layer, "line_lyr")
    arcpy.management.SelectLayerByLocation("line_lyr", "INTERSECT", buffer_shapefile)

    # Step 5: Copy selected lines
    arcpy.management.CopyFeatures("line_lyr", selected_lines)

    # Step 6: Export attribute tables to CSV
    points_table = os.path.join(output_folder, "points_table.csv")
    arcpy.conversion.TableToTable(points_layer, output_folder, "points_table.csv")

    lines_table = os.path.join(output_folder, "lines_table.csv")
    arcpy.conversion.TableToTable(selected_lines, output_folder, "lines_table.csv")

    # Step 7: Perform one-to-many join using pandas
    points_df = pd.read_csv(points_table)
    lines_df = pd.read_csv(lines_table)

    joined_df = pd.merge(lines_df, points_df, on="unique", how="left")

    # Step 8: Export joined table to CSV
    joined_df.to_csv(output_csv_path, index=False)

    # Step 9: Delete intermediate tables
    os.remove(points_table)
    os.remove(lines_table)

    # Set output CSV path for tool
    arcpy.SetParameterAsText(2, output_csv_path)

if __name__ == "__main__":
    # Get tool parameters
    csv_path = arcpy.GetParameterAsText(0)
    buffer_shapefile = arcpy.GetParameterAsText(1)
    output_csv_path = arcpy.GetParameterAsText(2)

    script_tool(csv_path, buffer_shapefile, output_csv_path)