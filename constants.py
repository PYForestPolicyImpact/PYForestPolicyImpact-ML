# Place all your constants here
import os

# Note: constants should be UPPER_CASE
constants_path = os.path.realpath(__file__)
SRC_PATH = os.path.dirname(constants_path)

PROJECT_PATH = os.path.dirname(SRC_PATH)

DATA_PATH = os.path.join(PROJECT_PATH,'data','policy-data')


# The larger study area to use for earth engine this study uses the western region of paraguay
STUDY_BOUNDARY_PATH = os.path.join(DATA_PATH, 'py-data','study_boundary', 'study_boundary.shp')

HANSEN_LOSSYEAR_FILEPATH =  os.path.join(DATA_PATH, 'raw-hansen', 'clipped_hansen_lossyear22.tif')

OUTPUT_PATH = os.path.join(DATA_PATH, 'raw-hansen')

HANSEN_TREECOVER_FILEPATH =  os.path.join(DATA_PATH, 'raw-hansen', 'clipped_hansen_treecover2000.tif')

TREECOVER_10_AND_ABOVE =  os.path.join(DATA_PATH, 'raw-hansen','tree_cover_10_percent_and_above', 'tree_cover_10_percent_and_above.tif')




LUP = os.path.join(DATA_PATH,'py-data', 'lup-limit','lup_gpkg','lup.gpkg')

LIMIT = os.path.join(DATA_PATH,'processing', 'original_limit', 'limite_put.shp')

LUP_SUBSET = os.path.join(DATA_PATH,'processing','lup_output','lup_subset_00_12.gpkg')

LIMIT_SUBSET = os.path.join(DATA_PATH,'processing','lup_output','limit_subset_clipped_boundaries.gpkg')

LUP_PRELABEL = os.path.join(DATA_PATH, 'processing','lup_output', 'almost_finished_lup_dataset.gpkg')

LUP_LABELED =  os.path.join(DATA_PATH, 'processing','lup_output', 'labeled_dataset.gpkg')

HANSEN_REPROJECTED = os.path.join(DATA_PATH, 'processing','hansen_output', 'hansen_reprojected.tiff')



CLEAN = os.path.join(DATA_PATH, 'processing', 'clean.gpkg')

DISSOLVED =  os.path.join(DATA_PATH, 'processing', 'dissolved_year.gpkg')


MODIFIED_RASTER = os.path.join(DATA_PATH, 'processing','hansen_output', 'final_modified_raster.tif')

GRUPO_RASTER =  os.path.join(DATA_PATH, 'processed_rasters','grupo', 'output_grupo_raster.tif')


DF_BY_YEAR_BINARY = os.path.join(DATA_PATH, 'raw-hansen', 'clipped_hansen_treecover2000.tif', 'deforestation_by_year_binary')