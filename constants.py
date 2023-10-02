# Place all your constants here
import os

# Note: constants should be UPPER_CASE
constants_path = os.path.realpath(__file__)
SRC_PATH = os.path.dirname(constants_path)

PROJECT_PATH = os.path.dirname(SRC_PATH)

DATA_PATH = os.path.join(PROJECT_PATH,'data','policy-data')


# The larger study area to use for earth engine this study uses the western region of paraguay
STUDY_BOUNDARY_PATH = os.path.join(DATA_PATH, 'study_boundary', 'study_boundary.shp')

HANSEN_LOSSYEAR_FILEPATH =  os.path.join(DATA_PATH, 'raw-hansen', 'clipped_hansen_lossyear22.tif')

OUTPUT_PATH = os.path.join(DATA_PATH, 'raw-hansen')

HANSEN_TREECOVER_FILEPATH =  os.path.join(DATA_PATH, 'raw-hansen', 'clipped_hansen_treecover2000.tif')

LIMIT = os.path.join(DATA_PATH,'lup-limit','limite_put.shp')

LUP = os.path.join(DATA_PATH,'lup-limit','catastro_forestal.shp')

LIMIT_SUBSET = os.path.join(DATA_PATH,'preprocessing', 'limit-subset.gpkg')

