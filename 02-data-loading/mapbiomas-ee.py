# %%
import os
import sys
import ee
import geemap
import json
from google.oauth2.service_account import Credentials
import geopandas as gpd


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
# Import SHAPEFILE_PATH from constants
from constants import STUDY_BOUNDARY_PATH

# %%
'''# Get the path to the service account JSON file from the environment variable
key_content  = os.environ.get('EEPRIVATE_KEY')
'''

# %%

'''# Parse the JSON content
key_dict = json.loads(key_content)
# Create credentials from the parsed JSON content
SCOPES = [
    'https://www.googleapis.com/auth/earthengine',
    'https://www.googleapis.com/auth/cloud-platform'
]
credentials = Credentials.from_service_account_info(key_dict, scopes=SCOPES)'''

#ee.Authenticate()
ee.Initialize()

# %%
imagery = ee.Image("projects/mapbiomas-chaco/public/collection4/mapbiomas_chaco_collection4_integration_v1")


# %%
imagery.bandNames()

# %%
chaco_2013 = imagery.select('classification_2013')
Map = geemap.Map()
Map.addLayer(chaco_2013,{}, 'Mapbiomas')
Map.center_object(chaco_2013)
Map

# %%
shapefile_path = STUDY_BOUNDARY_PATH
study_boundary = gpd.read_file(shapefile_path)

# %%
ee_boundary = geemap.geopandas_to_ee(study_boundary)



# %%

clipped_dataset = chaco_2013.clip(ee_boundary)


# %%
Map2 = geemap.Map()

centroid = ee_boundary.geometry().centroid().getInfo()['coordinates']
Map2.setCenter(centroid[0], centroid[1], 7)

Map2.addLayer(clipped_dataset, {}, 'MB Dataset Clipped')
Map2

# %%
clipped_dataset

# %%
# Extract the first feature from the FeatureCollection
ee_boundary_feature = ee_boundary.first()

# Get the geometry of the feature
ee_boundary_geometry = ee_boundary_feature.geometry()

# Get the coordinates of the geometry
ee_boundary_coordinates = ee_boundary_geometry.coordinates().getInfo()

# %%
export_params = {
    'scale': 30, # Resolution in meters
    'region': ee_boundary_coordinates, # Export only the region of interest
    'crs': 'EPSG:4326', # Coordinate reference system (optional)
    'fileFormat': 'GeoTIFF', # Export format (GeoTIFF or other supported formats)
    'fileNamePrefix': 'clipped_dataset13', # Prefix for the exported file name
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


# %%
# Your existing export task code
export_task = ee.batch.Export.image.toDrive(
    image=clipped_dataset.select('classification_2013'),
    description='classification_2013',
    folder='mb_data', # specify a folder in your Google Drive
    maxPixels=1e10,
    **export_params
)

export_task.start()

# %% [markdown]
#  https://code.earthengine.google.com/tasks

# %%
print(export_task.status())



