# %% [markdown]
# # Create Individual Deforestation Files From Hansen Dataset

# %% [markdown]
# The purpose of this notebook is two fold:
# 1. Extract pixels:Takes the 'lossyear' image from the Hansen et al. (2013) dataset and creates a tiff file deforestation_year for each year desired. Take the 'treecover2000' and filter for pixels greater than 10%. 
# 2. 'lossyear' and 'treecover2000' also need to be cropped so that pixels are only within the boundary of the active property of that year. 

# %% [markdown]
# # Import  libraries 

# %%
import os
import sys
from pathlib import Path
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.transform import from_origin
import geopandas as gpd
import pandas as pd
import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt


# %% [markdown]
# # Import Constants

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
from constants import HANSEN_LOSSYEAR_FILEPATH, STUDY_BOUNDARY_PATH, OUTPUT_PATH, HANSEN_TREECOVER_FILEPATH

# %%
study_boundary_gdf = gpd.read_file(STUDY_BOUNDARY_PATH)

'''rasterio.open() expects a single file path as a string, 
 pass the file path string directly. Since HANSEN_LOSSYEAR_FILEPATHS is a list, 
 you can access the file path string by indexing the list with [0].
 '''
# Reproject the study boundary to match the Hansen raster CRS
with rasterio.open(HANSEN_LOSSYEAR_FILEPATH) as src:
    hansen_crs = src.crs

# Reproject the study boundary GeoDataFrame to match the Hansen raster CRS    
study_boundary_gdf_reprojected = study_boundary_gdf.to_crs(hansen_crs)
# Get the geometry column from the reprojected GeoDataFrame
study_boundary_geom_reprojected = study_boundary_gdf_reprojected.geometry

# %%
with rasterio.open(HANSEN_LOSSYEAR_FILEPATH) as hansen:
    hansen_array = hansen.read(1)
    hansen_crs = hansen.crs
    out_transform = hansen.transform
    out_meta = hansen.meta

# %% [markdown]
# # Extract pixels corresponding to each year (2011-2021).

# %% [markdown]
# One-hot encoding is typically used for categorical variables, where there is no inherent ordering or numerical relationship between the categories. In your case, the year of deforestation does have an inherent ordering (i.e., 2007 comes before 2008) and possibly a numerical relationship (i.e., deforestation in earlier years might influence deforestation in later years), so treating it as a categorical variable might not be the best approach.
# 
# However, there is a nuance in your case. If a pixel gets deforested in a particular year, it remains deforested in all subsequent years. This means that a pixel deforested in 2007 will also be deforested in 2008, 2009, and so on. If you use the year of deforestation as a numeric value, you might be inadvertently suggesting that deforestation in 2008 is "more" or "greater" than deforestation in 2007, which is not necessarily the case. Instead, you're just tracking the first year of deforestation for each pixel.
# 
# Given this, you might consider the following approach:
# 
# Binary Encoding: For each year, create a binary raster indicating whether deforestation occurred in that year or not. This would give you a series of rasters with values of [0, 1] for each year.
# 
# Stacking: Stack these rasters together to create a 3D array (height x width x time), where each layer in the third dimension corresponds to a year. This way, the model can learn about the temporal dynamics of deforestation.
# 
# This approach allows the model to learn from the temporal sequence of deforestation events without misinterpreting the year of deforestation as a numerical value. However, it does not explicitly encode the information that once a pixel is deforested, it remains deforested in all subsequent years. You will need to ensure that your model architecture can capture this temporal dependency.
# 
# In the end, the choice of encoding often depends on the specifics of your data and the model you're using, and it may be worth experimenting with different approaches to see what works best.
# 

# %% [markdown]
# Lagged features are created by shifting the original feature values along the time dimension. They represent the values of a feature at an earlier time step. In the context of your deforestation problem, a lagged feature would represent whether deforestation occurred in a pixel in the previous year(s). By including these lagged features in your model, you allow the model to learn how deforestation in earlier years affects deforestation in later years.
# 
# Here's a step-by-step example of creating lagged features for your deforestation data:
# 
# Assume you have binary rasters for each year from 2001 to 2011, indicating whether deforestation occurred in that year (1) or not (0). You should have 11 rasters, one for each year.
# 
# To create a lagged feature with a lag of 1 year, you would shift the rasters by 1 year in the time dimension. For example, the 2002 raster would be shifted to 2001, the 2003 raster to 2002, and so on. The last raster (2011) would need to be filled with zeros or dropped, as there is no data available for 2012.
# 
# You should now have 11 rasters, where each raster represents whether deforestation occurred in the previous year (1) or not (0). These are the lagged features with a lag of 1 year.
# 
# Stack these new lagged rasters together with the original rasters. This would create a 3D array (height x width x 2 * time), where each layer in the third dimension corresponds to a year and its corresponding lagged year.
# 
# Use this new 3D array as input to your Random Forest model. The model will now learn the relationship between deforestation in the previous year(s) and the current year, which may help it better capture temporal dependencies.
# 
# In this example, I used a lag of 1 year, but you can experiment with different lag values depending on your data and problem. For instance, you could create lagged features for 2 or 3 years to capture longer-term dependencies.
# 
# Note that this is just one way to introduce temporal information into a non-temporal model like Random Forest. There might be other ways to incorporate temporal information, and it's worth experimenting to find the best approach for your data and problem.

# %%
'''This function accepts raster data, a start year, and an end year as arguments. 
The function iterates through the years within the given range and 
creates a binary mask for each year where the raster values match the year. 
It then stores these binary masks in a dictionary with the corresponding year 
as the key.'''



# Extract pixels corresponding to each year (2001-2021)
# This will return binary but if we want to keep the encoded value of the 
# pixelReturns pixels encoded with value of 1 and zeros as NaN.
#if `year_pixels[year_pixels == 0] = np.nan` is removed then will return 
# Unique values for year 2011: [0 1]. 

'''def extract_pixels_by_year_binary(raster_data, start_year, end_year):
    year_data = {}
    for year in range(start_year, end_year + 1):
        year_pixels = (raster_data == year).astype(int) 
        year_data[year] = year_pixels

        # Print unique values for each year
        unique_values = np.unique(year_pixels)
        print(f"Unique values for year {year + 2000}: {unique_values}") # Add 2000 to the year to get the correct year values
    return year_data

pixels_by_year = extract_pixels_by_year_binary(hansen_array, 22, 22)'''

'''While iterating through the years, the function also prints unique values for 
each year's binary mask. These unique values should be either 0 or 1, 
where 1 represents the pixels that have a deforestation event 
for that specific year, and 0 represents the pixels that do not.'''




# %% [markdown]
# Returns pixels encoded with value of corresponding year(11,12,13...) and zeros as NaN.
# if `year_pixels[year_pixels == 0] = np.nan` is removed then will return [0 11]. 

# %%
'''
def extract_pixels_by_year(raster_data, start_year, end_year):
    year_data = {}
    for year in range(start_year, end_year + 1):
        year_pixels = (raster_data == year).astype(int) * year
        year_data[year] = year_pixels

        # Print unique values for each year
        unique_values = np.unique(year_pixels)
        print(f"Unique values for year {year + 2000}: {unique_values}") # Add 2000 to the year to get the correct year values
             
    return year_data

pixels_by_year = extract_pixels_by_year(hansen_array, 11, 21)
'''


# %%
'''cumulative binary mask for each year, where the mask indicates which pixels match the current year 
or any previous year within the given range. pixels had an event in that year or any year before it.'''
'''def extract_pixels_by_year_cumulative(raster_data, start_year, end_year):
    year_data = {}
    cumulative_pixels = np.zeros_like(raster_data, dtype=int)
    
    for year in range(start_year, end_year + 1):
        year_pixels = (raster_data == year).astype(int)
        cumulative_pixels += year_pixels
        year_data[year] = cumulative_pixels.copy()

        # Print unique values for each year
        unique_values = np.unique(year_pixels)
        print(f"Unique values for year {year + 2000}: {unique_values}") # Add 2000 to the year to get the correct year values
    return year_data

pixels_by_year = extract_pixels_by_year_cumulative(hansen_array, 1, 22)'''


# %%
def extract_10year_deforestation(raster_data, start_year):
    cumulative_pixels = np.zeros_like(raster_data, dtype=int)
    
    # Loop through the 10-year interval
    for year in range(start_year, start_year + 10):
        year_pixels = (raster_data == year).astype(int)
        cumulative_pixels += year_pixels

    return cumulative_pixels

# Create a dictionary to store the 10-year datasets
ten_year_datasets = {}

# Loop through the years to generate the 10-year datasets
for start_year in range(1, 14):  # 1-10, 2-11, ... , 13-22
    ten_year_datasets[start_year] = extract_10year_deforestation(hansen_array, start_year)


# %% [markdown]
# # Write raster files for each year 
# write_year_rasters() takes four arguments: year_data, out_transform, out_meta, and output_dir. The year_data is a dictionary containing binary masks for each year, out_transform and out_meta are the transform and metadata extracted from the original Hansen loss year raster, and output_dir is the directory where the output raster files should be saved.
# 
# Inside the function,  loop through the year_data dictionary, and for each year,  create an output file path with a filename based on the year (e.g., 'deforestation_2001.tif'). Then, use rasterio.open() in write mode ('w') to create a new raster file with the specified metadata. write the binary mask data to the raster and set its transform to match the original raster.
# 
# After defining the function, create an output directory deforestation_by_year inside the OUTPUT_PATH directory using os.makedirs(). The exist_ok=True parameter ensures that the function does not raise an error if the directory already exists.
# 
# Finally, call the write_year_rasters() function, passing the pixels_by_year dictionary, out_transform, out_meta, and output_dir. The function writes separate raster files for each year's binary mask in the specified output directory.
# 

# %%
# Write raster files for each year
def write_year_rasters(year_data, out_transform, out_meta, output_dir):
    for year, data in year_data.items():
        out_filepath = os.path.join(output_dir, f'deforestation_{year}.tif')
        with rasterio.open(out_filepath, 'w', **out_meta) as dst:
            dst.write(data, 1)
            dst.transform = out_transform

output_dir = os.path.join(OUTPUT_PATH, 'deforestation_by_year_binary')
os.makedirs(output_dir, exist_ok=True)

write_year_rasters(pixels_by_year, out_transform, out_meta, output_dir)

# %%
# Write raster files for each year
def write_year_rasters(year_data, out_transform, out_meta, output_dir):
    for year, data in year_data.items():
        out_filepath = os.path.join(output_dir, f'deforestation_{year}-cumulative.tif')
        with rasterio.open(out_filepath, 'w', **out_meta) as dst:
            dst.write(data, 1)
            dst.transform = out_transform

output_dir = os.path.join(OUTPUT_PATH, 'deforestation_by_year_cumulative')
os.makedirs(output_dir, exist_ok=True)

write_year_rasters(pixels_by_year, out_transform, out_meta, output_dir)


# %%
# Write raster files for 10-year intervals
def write_10year_rasters(year_data, out_transform, out_meta, output_dir):
    for start_year, data in year_data.items():
        # Adjust the naming convention to reflect the 10-year interval
        end_year = start_year + 9
        out_filepath = os.path.join(output_dir, f'deforestation_{start_year}-{end_year}.tif')
        with rasterio.open(out_filepath, 'w', **out_meta) as dst:
            dst.write(data, 1)
            dst.transform = out_transform

# Define the output directory
output_dir = os.path.join(OUTPUT_PATH, 'deforestation_10year_intervals')
os.makedirs(output_dir, exist_ok=True)

# Call the adjusted function
write_10year_rasters(ten_year_datasets, out_transform, out_meta, output_dir)


# %%
# Read one of the TIF files and print its unique values
with rasterio.open("") as src:
    data = src.read(1)
print("Unique values in uncropped TIF:", np.unique(data))

# %% [markdown]
# # Extract Tree Cover >= 10%
# 
# To extract pixels with 10% and above tree cover and write the resulting raster:
# 
# 1. Read the tree cover raster data.
# 2. Create a binary mask for pixels with tree cover equal to or greater than 10%.
# 3. Write the binary mask to a new raster file.

# %%
# Step 1: Read the tree cover raster data
with rasterio.open(HANSEN_TREECOVER_FILEPATH) as src:
    tree_cover_array = src.read(1)
    tree_cover_transform = src.transform
    tree_cover_meta = src.meta

# Step 2: Create a mask for pixels with tree cover equal to or greater than 10%
'''np.where() to create a new array, masked_array,
that contains the original tree cover values 
where the condition (tree cover >= 10%) is met and 0 for the other pixels. '''
tree_cover_threshold = 10
masked_array = np.where(tree_cover_array >= tree_cover_threshold, tree_cover_array, 0)

# Step 3: Write the masked array to a new raster file
output_dir = os.path.join(OUTPUT_PATH, 'tree_cover_10_percent_and_above')
os.makedirs(output_dir, exist_ok=True)

output_filepath = os.path.join(output_dir, 'tree_cover_10_percent_and_above.tif')
with rasterio.open(output_filepath, 'w', **tree_cover_meta) as dst:
    dst.write(masked_array, 1)
    dst.transform = tree_cover_transform


