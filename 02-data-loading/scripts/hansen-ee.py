# %%
#1) Import all necessary packages
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import ee
import geemap
import geopandas as gpd


# %%
import os
import sys

# Get the current working directory
current_dir = os.path.abspath('')

# Search for the 'constants.py' file starting from the current directory and moving up the hierarchy
project_root = current_dir
while not os.path.isfile(os.path.join(project_root, 'constants.py')):
    project_root = os.path.dirname(project_root)

# Add the project root to the Python path
sys.path.append(project_root)




# %%
# Import SHAPEFILE_PATH from constants
from constants import STUDY_BOUNDARY_PATH

# %%
STUDY_BOUNDARY_PATH

# %% [markdown]
# # Import Hansen Dataset and Study Boundary
# 
# https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2022_v1_10
# 
# Hansen, M. C., P. V. Potapov, R. Moore, M. Hancher, S. A. Turubanova, A. Tyukavina, D. Thau, S. V. Stehman, S. J. Goetz, T. R. Loveland, A. Kommareddy, A. Egorov, L. Chini, C. O. Justice, and J. R. G. Townshend. 2013. "High-Resolution Global Maps of 21st-Century Forest Cover Change." Science 342 (15 November): 850-53. 10.1126/science.1244693 Data available on-line at: https://glad.earthengine.app/view/global-forest-change.

# %%
#ee.Authenticate()
ee.Initialize()

# %%
# load Hansen Global Forest Change v1.9 
imagery = ee.Image("UMD/hansen/global_forest_change_2022_v1_10")


# %%
Map = geemap.Map()

Map

# %%
Map.addLayer(imagery,{}, 'Hansen')

# %%
shapefile_path = STUDY_BOUNDARY_PATH
study_boundary = gpd.read_file(shapefile_path)


# %%
ee_boundary = geemap.geopandas_to_ee(study_boundary)



# %%
clipped_hansen_dataset = imagery.clip(ee_boundary)


# %%
Map = geemap.Map()
Map.centerObject(ee_boundary, zoom=10)
Map.addLayer(clipped_hansen_dataset, {'bands': ['lossyear'], 'palette': ['000000', '00FF00'], 'max': 100}, 'Hansen Dataset Clipped')
Map


# %%
num_bands = len(clipped_hansen_dataset.bandNames().getInfo())
print(f"Number of bands: {num_bands}")
# Get the band names from the clipped raster
band_names = clipped_hansen_dataset.bandNames().getInfo()

# Print the band names
print("Band names:")
for i, band in enumerate(band_names, 1):
    print(f"{i}. {band}")


# %% [markdown]
# **Dataset Details**
# This global dataset is divided into 10x10 degree tiles, consisting of seven files per tile. All files contain unsigned 8-bit values and have a spatial resolution of 1 arc-second per pixel, or approximately 30 meters per pixel at the equator.
# 
# **Tree canopy cover for year 2000 (treecover2000)**
# Tree cover in the year 2000, defined as canopy closure for all vegetation taller than 5m in height. Encoded as a percentage per output grid cell, in the range 0–100.
# 
# **Global forest cover gain 2000–2012 (gain)**
# Forest gain during the period 2000–2012, defined as the inverse of loss, or a non-forest to forest change entirely within the study period. Encoded as either 1 (gain) or 0 (no gain).
# 
# **Year of gross forest cover loss event (lossyear)**
# Forest loss during the period 2000–2020, defined as a stand-replacement disturbance, or a change from a forest to non-forest state. Encoded as either 0 (no loss) or else a value in the range 1–20, representing loss detected primarily in the year 2001–2020, respectively.
# 
# 
# **Data mask (datamask)**
# Three values representing areas of no data (0), mapped land surface (1), and permanent water bodies (2).
# 
# 
# **Circa year 2000 Landsat 7 cloud-free image composite (first)**
# Reference multispectral imagery from the first available year, typically 2000. If no cloud-free observations were available for year 2000, imagery was taken from the closest year with cloud-free data, within the range 1999–2012.
# 
# 
# **Circa year 2020 Landsat cloud-free image composite (last)**
# Reference multispectral imagery from the last available year, typically 2020. If no cloud-free observations were available for year 2020, imagery was taken from the closest year with cloud-free data.
# 
# 
# Reference composite imagery are median observations from a set of quality assessed growing season observations in four spectral bands, specifically Landsat bands 3, 4, 5, and 7. Normalized top-of-atmosphere (TOA) reflectance values (ρ) have been scaled to an 8-bit data range using a scale factor (g):
# 
# DN = ρ · g + 1
# The g factor was chosen independently for each band to preserve the band-specific dynamic range, as shown in the following table:
# 
# Landsat Band	       | g
# -----------------------|----
# Red (0.66 micrometers) | 508
# NIR (0.86 micrometers) | 254
# SWIR1 (1.6 micrometers)| 363
# SWIR2 (2.2 micrometers)| 423
# 
# 

# %%
export_params = {
    'scale': 30, # Resolution in meters
    'region': ee_boundary, # Export only the region of interest
    'crs': 'EPSG:4326', # Coordinate reference system (optional)
    'fileFormat': 'GeoTIFF', # Export format (GeoTIFF or other supported formats)
    'fileNamePrefix': 'clipped_hansen_dataset22', # Prefix for the exported file name
}
# Get the geometry and scale (resolution) of the clipped raster
geometry = ee_boundary.geometry()
scale = export_params['scale']

# Compute the pixel dimensions of the exported raster
dimensions = ee.Image.pixelLonLat().reproject(geometry.projection().atScale(scale)).reduceRegion(
    reducer=ee.Reducer.minMax(),
    geometry=geometry,
    scale=scale,
    maxPixels=1e10
).getInfo()

pixel_width = dimensions['longitude_max'] - dimensions['longitude_min']
pixel_height = dimensions['latitude_max'] - dimensions['latitude_min']

# Estimate the number of pixels
num_pixels = pixel_width * pixel_height
print(f"Number of pixels: {num_pixels}")

# Estimate the file size in bytes (assuming 4 bytes per pixel per band for GeoTIFF format)``
file_size_bytes = num_pixels * num_bands * 4
print(f"Estimated file size (bytes): {file_size_bytes}")





# %% [markdown]
# # Export Deforestation and TreeCover Files
# 
# 

# %%
# Extract the first feature from the FeatureCollection
ee_boundary_feature = ee_boundary.first()

# Get the geometry of the feature
ee_boundary_geometry = ee_boundary_feature.geometry()

# Get the coordinates of the geometry
ee_boundary_coordinates = ee_boundary_geometry.coordinates().getInfo()




# %%
# Update the export_params dictionary
export_params = {
    'scale': 30,
    'region': ee_boundary_coordinates,
    'crs': 'EPSG:4326',
    'fileFormat': 'GeoTIFF',
    'fileNamePrefix': 'clipped_hansen_lossyear22',
}

# Your existing export task code
export_task = ee.batch.Export.image.toDrive(
    image=clipped_hansen_dataset.select('lossyear'),
    description='lossyear',
    folder='hansen_data', # specify a folder in your Google Drive
    maxPixels=1e10,
    **export_params
)

export_task.start()

# %%
export_params = {
    'scale': 30, # Resolution in meters
    'region': ee_boundary_coordinates, # Export only the region of interest
    'crs': 'EPSG:4326', # Coordinate reference system (optional)
    'fileFormat': 'GeoTIFF', # Export format (GeoTIFF or other supported formats)
    'fileNamePrefix': 'clipped_hansen_dataset', # Prefix for the exported file name
}

export_task = ee.batch.Export.image.toDrive(
    image=clipped_hansen_dataset.select('treecover2000'),
    description='treecover2000',
    folder='hansen_data',  # specify a folder in your Google Drive
    maxPixels=1e10,
    **export_params
)
# Start the export task
export_task.start()


# %% [markdown]
# A new empty folder will appear in the google drive associated with Earth Engine account.
# The export process takes a considerable amount of time, progress can be monitored at
# https://code.earthengine.google.com/tasks


