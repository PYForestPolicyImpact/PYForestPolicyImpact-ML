# %%

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
from geopandas.tools import clip
from joblib import Parallel, delayed


# %%

# Get the current working directory
current_dir = os.path.abspath('')

# Search for the 'constants.py' file starting from the current directory and moving up the hierarchy
project_root = current_dir
while not os.path.isfile(os.path.join(project_root, 'constants.py')):
    project_root = os.path.dirname(project_root)

# Add the project root to the Python path
sys.path.append(project_root)

# %%
from constants import LIMIT, DATA_PATH, LIMIT_SUBSET, LUP

# %%
LIMIT_SUBSET

# %%
# Load the shapefile using geopandas
limit = gpd.read_file(LIMIT)



# %%
limit['anho_capa'] = limit['anho_capa'].astype(int)

limit = limit[['id', 'put_id', 'anho_capa','fecha_res', 'geometry' ]]

filtered_limit = limit[limit['anho_capa'] >= 2000]
filtered_limit['area'] = filtered_limit['geometry'].area

# %%
# Sort properties by registration year
properties = filtered_limit.sort_values(by='anho_capa')

# Convert fecha_res to datetime format
properties['fecha_res'] = pd.to_datetime(properties['fecha_res'], errors='coerce')

# For rows with NaT (Not a Timestamp) in fecha_res, assign a default date based on their year
properties.loc[properties['fecha_res'].isna(), 'fecha_res'] = pd.to_datetime(properties['anho_capa'].astype(str) + '-01-01')

# Sort properties by fecha_res
properties = properties.sort_values(by='fecha_res')


# %%
# Create an empty GeoDataFrame to store the final processed properties
final_properties = gpd.GeoDataFrame(columns=properties.columns)

# Add properties from the year 2000 to final_properties as the baseline
final_properties = pd.concat([final_properties, properties[properties['anho_capa'] == 2000]])

for year in range(2001, 2023):  # Loop from 2001 to 2022
    # Get properties of the current year
    current_year_properties = properties[properties['anho_capa'] == year]
    
    # Iterate over each property of the current year
    for idx, current_property in current_year_properties.iterrows():
        # Subtract geometries of older properties from the current property
        for _, older_property in final_properties.iterrows():
            current_property['geometry'] = current_property['geometry'].difference(older_property['geometry'])
        
        # Append the "cut" current property to the final_properties GeoDataFrame
        final_properties = pd.concat([final_properties, current_property.to_frame().T])
final_properties.crs = properties.crs

# %%
output_path = os.path.join(DATA_PATH,'preprocessing' "dataset-clip")

# Convert the 'fecha_res' column to a string format
final_properties['fecha_res'] = final_properties['fecha_res'].astype(str)

# Create the directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)
    # Save the GeoDataFrame as a GeoPackage
# Define the filename for the GeoPackage

filename = os.path.join(output_path, "datset-clip.gpkg")
final_properties.to_file(filename, driver="GPKG")

# %%
output_path = os.path.join(DATA_PATH, "limit-subsets")
# Create the directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)

for year in sorted(filtered_limit['anho_capa'].unique()):
    year_gdf = filtered_limit[filtered_limit['anho_capa'] == year]
    
    # Define the filename for the GeoPackage
    filename = os.path.join(output_path, f"year_{year}.gpkg")
    
    # Save the GeoDataFrame as a GeoPackage
    year_gdf.to_file(filename, driver="GPKG")

# %%
# Load the shapefile using geopandas
limit_subset = gpd.read_file(LIMIT_SUBSET)
lup  = gpd.read_file(LUP)

# %%
len(limit_subset['put_id'].unique())

# %%
'''keep=False: This argument specifies how to mark duplicates:
If keep='first' (default), it would mark all duplicates as True except for the first occurrence.
If keep='last', it would mark all duplicates as True except for the last occurrence.
If keep=False, it marks all duplicates as True.
'''
print(limit_subset[limit_subset.duplicated(subset='put_id', keep=False)])


# %%
# Filter out rows with empty geometries
limit_subset = limit_subset[~limit_subset.geometry.is_empty]

# Reset the index if needed
limit_subset.reset_index(drop=True, inplace=True)


# %%
len(limit_subset['put_id'].unique())

# %%
# Extract the unique 'put_id' values from limit_subset
put_ids_to_subset = limit_subset['put_id'].unique()

# Subset the lup DataFrame based on these put_id values
lup_subset = lup[lup['put_id'].isin(put_ids_to_subset)]


# %%
# Check for invalid geometries in lup and limit_subset
invalid_lup = lup_subset[~lup_subset.geometry.is_valid]
invalid_limit = limit_subset[~limit_subset.geometry.is_valid]

# If there are invalid geometries, you might want to repair them
# One common method is to use the buffer operation with a distance of 0
if not invalid_lup.empty:
    lup_subset.geometry = lup_subset.buffer(0)

if not invalid_limit.empty:
    limit_subset.geometry = limit_subset.buffer(0)


# %%
invalid_lup

# %%
not invalid_lup.empty


# %%
not invalid_limit.empty

# %%
# Create an empty GeoDataFrame to store the clipped lup polygons
final_properties = gpd.GeoDataFrame(columns=lup.columns, crs=lup.crs)

# Outer loop: Iterate through each geometry in limit_subset
for _, row in limit_subset.iterrows():
    current_limit_geom = row.geometry
    current_put_id = row['put_id']
    
    # Gather all the lup_subset polygons with the same put_id
    current_lup_polygons = lup_subset[lup_subset['put_id'] == current_put_id]
    
    # Clip the gathered lup polygons using the current limit_subset geometry
    clipped_lup = gpd.clip(current_lup_polygons, current_limit_geom)
    
    # Append the clipped lup polygons to the final_properties GeoDataFrame
    final_properties = pd.concat([final_properties, clipped_lup])

# Reset the index of the result GeoDataFrame
final_properties.reset_index(drop=True, inplace=True)


# %%
output_path = os.path.join(DATA_PATH,'preprocessing' )


# Create the directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)
    # Save the GeoDataFrame as a GeoPackage
# Define the filename for the GeoPackage

filename = os.path.join(output_path, "analysis_subset.gpkg")
final_properties.to_file(filename, driver="GPKG")


