# %% [markdown]
# # Geospatial Data Processing Methodology
# 
# Methodology employed for processing geospatial data using the GeoPandas library in Python. The primary objective was to refine and clip polygons from the Land Use Plan (LUP) dataset based on boundaries defined in the Limit Subset dataset, ensuring non-overlapping property polygons.
# 
# 2. Data Preparation
# 2.1. Property Filtering and Sorting:
# 
# The dataset was filtered to retain properties registered from the year 2000 onwards.
# Properties were sorted chronologically, first by their registration year (anho_capa) and subsequently by their registration date (fecha_res).
# 2.2. Baseline Establishment:
# 
# An initial set of properties from the year 2000 was used to establish a baseline in the final_properties GeoDataFrame.
# 3. Data Processing
# 3.1. Polygon Subtraction:
# 
# For each subsequent year (2001-2022), the following steps were undertaken:
# The geometries of older properties were subtracted from the current property to ensure no overlaps.
# The modified current property was appended to the final_properties GeoDataFrame.
# 3.2. Yearly Subsets Creation:
# 
# The dataset was segmented into yearly subsets. Each subset was saved as a separate GeoPackage for granularity.
# 3.3. Data Validation:
# 
# Duplicate put_id values in the limit_subset dataset were identified and addressed.
# Rows with empty geometries were filtered out.
# A subset of the LUP dataset, termed lup_subset, was created based on unique put_id values from limit_subset.
# 3.4. Geometry Validation and Repair:
# 
# Invalid geometries in both the lup_subset and limit_subset datasets were identified.
# A buffer operation was employed to repair any detected invalid geometries.
# 4. Clipping Process
# 4.1. Polygon Clipping:
# 
# For each geometry in the limit_subset dataset:
# Corresponding polygons from the lup_subset were identified.
# These polygons were then clipped based on the current limit_subset geometry's boundaries.
# The resulting clipped polygons were appended to the final_properties GeoDataFrame.
# 5. Final Output
# 5.1. Saving Processed Data:
# 
# The final_properties GeoDataFrame, which houses the clipped polygons, was saved as a GeoPackage. This dataset is primed for subsequent analysis or visualizatio

# %%

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
from geopandas.tools import clip
from joblib import Parallel, delayed
import numpy as np

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
from constants import  DATA_PATH, LUP, LIMIT, LUP_SUBSET,LIMIT_SUBSET, LUP_PRELABEL

# %%
# Load the shapefile using geopandas
limit = gpd.read_file(LIMIT)
lup = gpd.read_file(LUP)


# %%
limit['anho_capa'] = limit['anho_capa'].astype(int)

limit = limit[['id', 'put_id', 'anho_capa','fecha_res', 'geometry' ]]

filtered_limit = limit[(limit['anho_capa'] >= 2000) & (limit['anho_capa'] <= 2013)]
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
properties

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
output_path = os.path.join(DATA_PATH,'processing')

# Convert the 'fecha_res' column to a string format
final_properties['fecha_res'] = final_properties['fecha_res'].astype(str)

# Create the directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)
    # Save the GeoDataFrame as a GeoPackage
# Define the filename for the GeoPackage

filename = os.path.join(output_path, "datset-clip.gpkg")
final_properties.to_file(filename, driver="GPKG")

# %% [markdown]
#  output processed in Qgis, Four buffers of 150 m
# (negative,positive, negative,positive)
# Some missing properties  reacquired
# processed dataset brougth back in

# %%
# Not used
'''output_path = os.path.join(DATA_PATH, "limit-subsets")
# Create the directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)

for year in sorted(filtered_limit['anho_capa'].unique()):
    year_gdf = filtered_limit[filtered_limit['anho_capa'] == year]
    
    # Define the filename for the GeoPackage
    filename = os.path.join(output_path, f"year_{year}.gpkg")
    
    # Save the GeoDataFrame as a GeoPackage
    year_gdf.to_file(filename, driver="GPKG")'''

# %%
# Load the shapefile using geopandas
limit_subset = gpd.read_file(LIMIT_SUBSET)
lup_subset  = gpd.read_file(LUP_SUBSET)


# %%
lup_subset

# %%
len(limit_subset['put_id'].unique())

# %%
len(lup_subset['put_id'].unique())

# %%
'''keep=False: This argument specifies how to mark duplicates:
If keep='first' (default), it would mark all duplicates as True except for the first occurrence.
If keep='last', it would mark all duplicates as True except for the last occurrence.
If keep=False, it marks all duplicates as True.
'''
print(limit_subset[limit_subset.duplicated(subset='put_id', keep=False)])


# %%
limit_subset.geometry.is_empty

# %%
limit_subset.geometry.is_empty.sum()

# %%
# Save the rows with empty geometries
empty_geometries = limit_subset[limit_subset.geometry.is_empty]

# Filter out rows with empty geometries
limit_subset = limit_subset[~limit_subset.geometry.is_empty]

# Reset the index if needed
limit_subset.reset_index(drop=True, inplace=True)


# %%
empty_geometries

# %%
len(limit_subset['put_id'].unique())

# %%
# Check for invalid geometries in lup and limit_subset
invalid_lup = lup_subset[~lup_subset.geometry.is_valid]
invalid_limit = limit_subset[~limit_subset.geometry.is_valid]

# %%
invalid_limit

# %%
invalid_lup

# %%


# If there are invalid geometries, you might want to repair them
# One common method is to use the buffer operation with a distance of 0
if not invalid_lup.empty:
    lup_subset.geometry = lup_subset.buffer(0)

if not invalid_limit.empty:
    limit_subset.geometry = limit_subset.buffer(0)


# %%
# Check for invalid geometries in lup and limit_subset
invalid_lup = lup_subset[~lup_subset.geometry.is_valid]
invalid_limit = limit_subset[~limit_subset.geometry.is_valid]

# %%
invalid_lup

# %%
invalid_limit

# %%
invalid_lup.empty


# %%
invalid_limit.empty

# %%
# Initially, lup_subset contains all land use plans
# Keep a copy of the original lup_subset before filtering
original_lup_subset = lup_subset.copy()

# %%
# Extract the unique 'put_id' values from limit_subset
put_ids_to_subset = limit_subset['put_id'].unique()


# Filter lup_subset to only include land use plans with a corresponding property border
lup_subset = lup_subset[lup_subset['put_id'].isin(put_ids_to_subset)]


# Find the land use plans that were excluded in the filtering process
excluded_lup = original_lup_subset[~original_lup_subset['put_id'].isin(put_ids_to_subset)]



# %%
excluded_lup


# %%
len(original_lup_subset['put_id'].unique())

# %%
len(lup_subset['put_id'].unique())

# %%
len(excluded_lup['put_id'].unique())

# %%
1339+173

# %%
limit_subset

# %%
lup_subset

# %%
limit_subset.crs

# %%
lup_subset.crs

# %%
lup_subset=lup_subset.to_crs(limit_subset.crs)

# %%
lup_subset.crs

# %%
excluded_lup.crs

# %%
excluded_lup = excluded_lup.to_crs(limit_subset.crs)

# %%
excluded_lup.crs

# %%
len(lup_subset[~lup_subset.geometry.is_valid])

# %%
# If there are invalid geometries, you might want to repair them
if not invalid_lup.empty:
    lup_subset.geometry = lup_subset.buffer(-1)

# %%
lup_subset.geometry = lup_subset.buffer(1)

# %%
len(lup_subset[~lup_subset.geometry.is_valid])

# %%
# Create an empty GeoDataFrame to store the clipped lup polygons
final_properties = gpd.GeoDataFrame(columns=lup_subset.columns, crs=lup_subset.crs)

# Outer loop: Iterate through each geometry in limit_subset
for _, row in limit_subset.iterrows():
    current_limit_geom = row.geometry
    current_put_id = row['put_id']
    
    # Gather all the lup_subset polygons with the same put_id
    current_lup_polygons = lup_subset[lup_subset['put_id'] == current_put_id]
    
    # Clip the gathered lup polygons using the current limit_subset geometry
    clipped_lup = gpd.clip(current_lup_polygons, current_limit_geom)
    
    # Ensure the clipped_lup has the same CRS as final_properties before concatenating
    clipped_lup = clipped_lup.to_crs(final_properties.crs)
    
    # Append the clipped lup polygons to the final_properties GeoDataFrame
    final_properties = pd.concat([final_properties, clipped_lup])

# Reset the index of the result GeoDataFrame
final_properties.reset_index(drop=True, inplace=True)


# %%
# Append the excluded lup polygons to the final_properties GeoDataFrame
'''final_properties = pd.concat([final_properties, excluded_lup])

# Reset the index of the result GeoDataFrame
final_properties.reset_index(drop=True, inplace=True)'''


# %%
len(final_properties['put_id'].unique())

# %%
# Merge fecha_res from limit to lup based on put_id
lup_filtered_fres = final_properties.merge(limit_subset[['put_id', 'fecha_res']], on='put_id', how='left')

# %%
len(lup_filtered_fres['put_id'].unique())

# %%
output_path = os.path.join(DATA_PATH,'processing' )


# Create the directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)
    # Save the GeoDataFrame as a GeoPackage
# Define the filename for the GeoPackage

filename = os.path.join(output_path, "analysis_ready_subset.gpkg")
lup_filtered_fres.to_file(filename, driver="GPKG")

# %%
len(excluded_lup[~excluded_lup.geometry.is_valid])

# %%
output_path = os.path.join(DATA_PATH,'processing' )


# Create the directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)
    # Save the GeoDataFrame as a GeoPackage
# Define the filename for the GeoPackage

filename = os.path.join(output_path, "excluded_lup.gpkg")
excluded_lup.to_file(filename, driver="GPKG")

# %% [markdown]
# I used the excluded and final properties to see what was missed during the process in qgis. From this i decided that using the lup_subset and taking the difference was the best route as that gave me all the lup plans that were missed. applied a -45 and 45 buffer. Manually stil had to clean lups that overlapped, for most part they were just duplicates in some cases they were from different years. In the case of different years I selected the oldest lup.

# %%
prelabel = gpd.read_file(LUP_PRELABEL)

# %%
prelabel

# %%
# Step 1: Identify the unique values of 'categoria_ant' for each 'grupo'
unique_values_mapping = prelabel.groupby('grupo')['categoria_ant'].unique().to_dict()

# %%
unique_values_mapping

# %%
# Given unique_values_mapping as a dictionary from your previous code:
unique_values_mapping = {
    'AREA_AUTORIZADA': np.array(['A-HABILITAR', 'SIN COBERTURA']),
    'BOSQUES': np.array(['FRANJAS', 'RESERVA-FORESTAL', 'PROTECCION-CAUCES', 'PROTECCION',
                         'BOSQUETES', 'REGENERACION', 'FORESTACION', 'A-REFORESTAR',
                         'REMANENTE', 'REFORESTACION', 'A-REGENERAR', 'MANEJO-FORESTAL']),
    'EN_CONFLICTO': np.array(['EN-CONFLICTO']),
    'OTRAS_COBERTURAS': np.array(['NO_FORESTAL', 'PASTO', 'AREA AFECTADA POR M*']),
    'OTRAS_TIERRAS_FORESTALES': np.array(['MATORRAL', 'PALMARES'])
}

# Create a mapping dictionary for 'categoria_ant' values
categoria_ant_to_grupo = {}
for grupo, categorias in unique_values_mapping.items():
    for categoria in categorias.tolist():  # Convert numpy array to list before iterating
        categoria_ant_to_grupo[categoria] = grupo

# Adjust the mapping for 'EN_CONFLICTO'
categoria_ant_to_grupo['EN-CONFLICTO'] = 'BOSQUES'

# Fill in the empty rows of 'grupo'
prelabel.loc[prelabel['grupo'].isna(), 'grupo'] = prelabel.loc[prelabel['grupo'].isna(), 'categoria_ant'].map(categoria_ant_to_grupo)


# %%
# Count the number of NaN values in the 'grupo' column
number_of_nans = prelabel['grupo'].isna().sum()

# Print the result
print(f"Number of NaN values in 'grupo' column: {number_of_nans}")


# %%
# Identify the unique 'categoria_ant' values where 'grupo' is NaN
missing_categories = prelabel[prelabel['grupo'].isna()]['categoria_ant'].unique()

# Print the missing categories
print("Missing categories that were not mapped:")
print(missing_categories)


# %%
# Check if all NaN values in 'categoria_ant' correspond to NaN values in 'grupo'
nan_correspondence_check = prelabel[prelabel['categoria_ant'].isna()]['grupo'].isna().all()

# Print the result of the check
print(f"All NaN values in 'categoria_ant' correspond to NaN values in 'grupo': {nan_correspondence_check}")

# Assign 'B-INUNDABLE' and 'CAMINO' to 'OTRAS_COBERTURAS' if 'grupo' is NaN
prelabel.loc[(prelabel['categoria_ant'].isin(['B-INUNDABLE', 'CAMINO'])) & (prelabel['grupo'].isna()), 'grupo'] = 'OTRAS_COBERTURAS'

# Re-check the number of NaN values in the 'grupo' column after the operation
number_of_nans_after = prelabel['grupo'].isna().sum()

# Print the result
print(f"Number of NaN values in 'grupo' column after the operation: {number_of_nans_after}")


# %%
# Fill in the remaining NaN values in 'grupo' with 'OTRAS_COBERTURAS'
prelabel['grupo'].fillna('OTRAS_COBERTURAS', inplace=True)

# Re-check the number of NaN values in the 'grupo' column after the operation
number_of_nans_final = prelabel['grupo'].isna().sum()

# Print the result
print(f"Number of NaN values in 'grupo' column after final operation: {number_of_nans_final}")


# %%
prelabel.columns

# %%
prelabel

# %%
selected_columns_df = prelabel[['anho_capa', 'put_id', 'fecha_res', 'grupo', 'geometry']]

# %%
output_path = os.path.join(DATA_PATH,'processing' )


# Create the directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)
    # Save the GeoDataFrame as a GeoPackage
# Define the filename for the GeoPackage

filename = os.path.join(output_path, "labeled_dataset.gpkg")
selected_columns_df.to_file(filename, driver="GPKG")


