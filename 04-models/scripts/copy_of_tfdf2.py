# -*- coding: utf-8 -*-
"""Copy of tfdf2

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1WMIgkrY1dStlwMHVV5qiDnnPENf2LYlp
"""

!pip install rasterio

!pip install imblearn

!pip install scikit-learn

#from google.colab import drive
#drive.mount('/content/drive')

import os
import numpy as np
import pandas as pd
import tensorflow as tf
import math
import matplotlib.pyplot as plt

from IPython.core.magic import register_line_magic
from IPython.display import Javascript
from IPython.display import display as ipy_display

import rasterio
import pandas as pd
import joblib
from joblib import dump

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (confusion_matrix, classification_report, accuracy_score,
                             precision_score, recall_score, f1_score, roc_auc_score,
                             precision_recall_curve, roc_curve, auc)
from sklearn.model_selection import (train_test_split, cross_val_score,
                                     GridSearchCV, RandomizedSearchCV)
from sklearn.preprocessing import OneHotEncoder, FunctionTransformer
from sklearn.pipeline import make_pipeline
from sklearn.compose import make_column_transformer
from sklearn.metrics import ConfusionMatrixDisplay
from sklearn.model_selection import StratifiedKFold


from scipy.stats import randint as sp_randint
from scipy.stats import uniform as sp_uniform

from imblearn.ensemble import BalancedRandomForestClassifier

from scipy.stats import skew

# Some of the model training logs can cover the full
# screen if not compressed to a smaller viewport.
# This magic allows setting a max height for a cell.
@register_line_magic
def set_cell_height(size):
  ipy_display(
      Javascript("google.colab.output.setIframeHeight(0, true, {maxHeight: " +
                 str(size) + "})"))

FEATURES_DIR = '/content/drive/MyDrive/data/training/'
EXCLUDE_FILE = 'train_binary_deforestation_raster.tif'

# Path to the y_file
y_file = os.path.join(FEATURES_DIR, 'train_binary_deforestation_raster.tif')

# Helper function to read TIFF files
def read_tiff_image(file_path):
    with rasterio.open(file_path) as src:
        return src.read(1)

# List of paths to the raster files excluding the specified file
feature_files = [os.path.join(FEATURES_DIR, file_name)
                 for file_name in os.listdir(FEATURES_DIR)
                 if file_name != EXCLUDE_FILE]

# Read and store each raster file's data in an array
#feature_data_arrays = [read_tiff_image(file_path) for file_path in feature_files]

feature_files = [os.path.join(FEATURES_DIR, file_name)
                 for file_name in os.listdir(FEATURES_DIR)
                 if file_name != EXCLUDE_FILE]
feature_files

# Read the feature rasters and stack them into a single array
X = np.stack([read_tiff_image(file_path) for file_path in feature_files])

# Read the target raster
with rasterio.open(y_file) as src:
    y = src.read(1)

# Flatten the arrays and remove nodata values
nodata_mask = np.any(X == -1, axis=0)
X = X[:, ~nodata_mask].T
y = y[~nodata_mask]

# Define the indices of the categorical features (grupo and soil)
grupo_index = feature_files.index('/content/drive/MyDrive/data/training/train_grupo_masked.tif')
soil_index = feature_files.index('/content/drive/MyDrive/data/training/train_soil_masked.tif')

# Define the indices of the features that need log transformation (river, cities, roads)
log_indices = [
    feature_files.index('/content/drive/MyDrive/data/training/train_river_distance_raster.tif'),
    feature_files.index('/content/drive/MyDrive/data/training/train_cities_masked.tif'),
    feature_files.index('/content/drive/MyDrive/data/training/train_road_distance_raster.tif')
]

# Create a column transformer for preprocessing
preprocessor = make_column_transformer(
    (OneHotEncoder(), [grupo_index, soil_index]),  # One-hot encode categorical features
    (FunctionTransformer(np.log1p), log_indices),  # Apply log transformation
    remainder='passthrough'  # Pass the remaining features as is
)
# Apply the preprocessing steps to the entire dataset
X_preprocessed = preprocessor.fit_transform(X)



del X
del feature_files
#del feature_data_arrays
del grupo_index
del soil_index
del log_indices
del preprocessor

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X_preprocessed, y, train_size =0.05, stratify=y, random_state=42)

del X_preprocessed
del y

print(X_train.shape)
print(X_test.shape)
print(y_train.shape)
print(y_test.shape)

from sklearn.utils.parallel import delayed, Parallel
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, message="Function delayed is deprecated")
warnings.filterwarnings("ignore", category=UserWarning, message="`sklearn.utils.parallel.delayed` should be used with `sklearn.utils.parallel.Parallel`")
from sklearn.utils.class_weight import compute_class_weight

# Define the updated parameter grid
param_grid = {
    'balancedrandomforestclassifier__n_estimators': sp_randint(100, 1000),
    'balancedrandomforestclassifier__max_depth': [None] + list(range(10, 51)),
    'balancedrandomforestclassifier__min_samples_split': sp_randint(2, 21),
    'balancedrandomforestclassifier__min_samples_leaf': sp_randint(1, 21),
    'balancedrandomforestclassifier__max_features': ['sqrt', 'log2', None] + list(np.arange(0.2, 1.0, 0.1)),
    'balancedrandomforestclassifier__criterion': ['gini', 'entropy']
}

# Compute class weights on the full training set or a large enough sample
sample_size = min(len(y_train), 10000)  # Adjust the sample size as needed
sample_indices = np.random.choice(len(y_train), size=sample_size, replace=False)
sample_y = y_train[sample_indices]

class_weights = compute_class_weight("balanced", classes=np.unique(sample_y), y=sample_y)
class_weight_dict = dict(zip(np.unique(sample_y), class_weights))

# Create the pipeline
pipeline = make_pipeline(
    BalancedRandomForestClassifier(random_state=42, class_weight=class_weight_dict, warm_start=True, bootstrap=False, replacement=True)
)

# Initialize the number of iterations and data size
n_iter = 50
data_size = 2000

# Create the StratifiedKFold object
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)


# Set scoring metrics
scoring = {
    'precision': 'precision',
    'recall': 'recall',
    'f1': 'f1',
    'roc_auc': 'roc_auc'
}

# Iterate and narrow down the grid
for _ in range(3):  # Number of iterations to narrow down the grid
    # Sample a subset of data for the current iteration
    idx = np.random.choice(X_train.shape[0], size=data_size, replace=False)
    X_subset = X_train[idx]
    y_subset = y_train[idx]

    # Create the RandomizedSearchCV object
    random_search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=param_grid,
        n_iter=n_iter,
        cv=skf,
        scoring=scoring,
        refit='f1',
        n_jobs=1,
        random_state=42,
        verbose=1
    )

    # Fit the RandomizedSearchCV object on the subset of data
    random_search.fit(X_subset, y_subset)

    # Get the best parameters and best score for the current iteration
    best_params = random_search.best_params_
    best_score = random_search.best_score_
    best_estimator = random_search.best_estimator_

    print(f"Iteration best parameters: {best_params}")
    print(f"Iteration best score: {best_score}")
    print(f"Iteration best estimator: {best_estimator}")

    # Update the parameter grid based on the best parameters
    if isinstance(best_params['balancedrandomforestclassifier__max_features'], str):
      max_features_values = ['sqrt', 'log2', None]
    else:
      max_features_values = list(np.arange(max(0.1, float(best_params['balancedrandomforestclassifier__max_features']) - 0.2), min(1.0, float(best_params['balancedrandomforestclassifier__max_features']) + 0.2), 0.1))

      # Update the parameter grid based on the best parameters
    param_grid = {
        'balancedrandomforestclassifier__n_estimators': sp_randint(max(100, best_params['balancedrandomforestclassifier__n_estimators'] - 100), best_params['balancedrandomforestclassifier__n_estimators'] + 100),
        'balancedrandomforestclassifier__max_depth': [best_params['balancedrandomforestclassifier__max_depth']] + list(range(max(10, best_params['balancedrandomforestclassifier__max_depth'] - 10), min(51, best_params['balancedrandomforestclassifier__max_depth'] + 11))),
        'balancedrandomforestclassifier__min_samples_split': sp_randint(max(2, best_params['balancedrandomforestclassifier__min_samples_split'] - 4), best_params['balancedrandomforestclassifier__min_samples_split'] + 5),
        'balancedrandomforestclassifier__min_samples_leaf': sp_randint(max(1, best_params['balancedrandomforestclassifier__min_samples_leaf'] - 4), best_params['balancedrandomforestclassifier__min_samples_leaf'] + 5),
        'balancedrandomforestclassifier__max_features': max_features_values,
        'balancedrandomforestclassifier__criterion': ['gini', 'entropy']
    }

    # Increase the data size for the next iteration
    data_size *= 2

# Get the overall best parameters and best score
best_params = random_search.best_params_
best_score = random_search.best_score_
best_estimator = random_search.best_estimator_
print("Overall best parameters: ", best_params)
print("Overall best score: ", best_score)
print("Overall best estimator: ", best_estimator)

from sklearn.utils.parallel import delayed, Parallel
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, message="Function delayed is deprecated")
warnings.filterwarnings("ignore", category=UserWarning, message="`sklearn.utils.parallel.delayed` should be used with `sklearn.utils.parallel.Parallel`")
from sklearn.utils.class_weight import compute_class_weight

# Define the updated parameter grid
param_grid = {
    'balancedrandomforestclassifier__n_estimators': sp_randint(100, 1000),
    'balancedrandomforestclassifier__max_depth': [None] + list(range(10, 51)),
    'balancedrandomforestclassifier__min_samples_split': sp_randint(2, 21),
    'balancedrandomforestclassifier__min_samples_leaf': sp_randint(1, 21),
    'balancedrandomforestclassifier__max_features': ['sqrt', 'log2', None] + list(np.arange(0.2, 1.0, 0.1)),
    'balancedrandomforestclassifier__criterion': ['gini', 'entropy']
}

# Compute class weights on the full training set or a large enough sample
sample_size = min(len(y_train), 10000)  # Adjust the sample size as needed
sample_indices = np.random.choice(len(y_train), size=sample_size, replace=False)
sample_y = y_train[sample_indices]

class_weights = compute_class_weight("balanced", classes=np.unique(sample_y), y=sample_y)
class_weight_dict = dict(zip(np.unique(sample_y), class_weights))

# Create the pipeline
pipeline = make_pipeline(
    BalancedRandomForestClassifier(random_state=42, class_weight=class_weight_dict, warm_start=True, bootstrap=False, replacement=True)
)

# Initialize the number of iterations and data size
n_iter = 50
data_size = 10000

# Create the StratifiedKFold object
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)


# Set scoring metrics
scoring = {
    'precision': 'precision',
    'recall': 'recall',
    'f1': 'f1',
    'roc_auc': 'roc_auc'
}

# Iterate and narrow down the grid
for _ in range(3):  # Number of iterations to narrow down the grid
    # Sample a subset of data for the current iteration
    idx = np.random.choice(X_train.shape[0], size=data_size, replace=False)
    X_subset = X_train[idx]
    y_subset = y_train[idx]

    # Create the RandomizedSearchCV object
    random_search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=param_grid,
        n_iter=n_iter,
        cv=skf,
        scoring=scoring,
        refit='f1',
        n_jobs=1,
        random_state=42,
        verbose=1
    )

    # Fit the RandomizedSearchCV object on the subset of data
    random_search.fit(X_subset, y_subset)

    # Get the best parameters and best score for the current iteration
    best_params = random_search.best_params_
    best_score = random_search.best_score_
    best_estimator = random_search.best_estimator_

    print(f"Iteration best parameters: {best_params}")
    print(f"Iteration best score: {best_score}")
    print(f"Iteration best estimator: {best_estimator}")

    # Update the parameter grid based on the best parameters
    if isinstance(best_params['balancedrandomforestclassifier__max_features'], str):
      max_features_values = ['sqrt', 'log2', None]
    else:
      max_features_values = list(np.arange(max(0.1, float(best_params['balancedrandomforestclassifier__max_features']) - 0.2), min(1.0, float(best_params['balancedrandomforestclassifier__max_features']) + 0.2), 0.1))

      # Update the parameter grid based on the best parameters
    param_grid = {
        'balancedrandomforestclassifier__n_estimators': sp_randint(max(100, best_params['balancedrandomforestclassifier__n_estimators'] - 100), best_params['balancedrandomforestclassifier__n_estimators'] + 100),
        'balancedrandomforestclassifier__max_depth': [best_params['balancedrandomforestclassifier__max_depth']] + list(range(max(10, best_params['balancedrandomforestclassifier__max_depth'] - 10), min(51, best_params['balancedrandomforestclassifier__max_depth'] + 11))),
        'balancedrandomforestclassifier__min_samples_split': sp_randint(max(2, best_params['balancedrandomforestclassifier__min_samples_split'] - 4), best_params['balancedrandomforestclassifier__min_samples_split'] + 5),
        'balancedrandomforestclassifier__min_samples_leaf': sp_randint(max(1, best_params['balancedrandomforestclassifier__min_samples_leaf'] - 4), best_params['balancedrandomforestclassifier__min_samples_leaf'] + 5),
        'balancedrandomforestclassifier__max_features': max_features_values,
        'balancedrandomforestclassifier__criterion': ['gini', 'entropy']
    }

    # Increase the data size for the next iteration
    data_size *= 2

# Get the overall best parameters and best score
best_params = random_search.best_params_
best_score = random_search.best_score_
best_estimator = random_search.best_estimator_
print("Overall best parameters: ", best_params)
print("Overall best score: ", best_score)
print("Overall best estimator: ", best_estimator)

from sklearn.utils.parallel import delayed, Parallel
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, message="Function delayed is deprecated")
warnings.filterwarnings("ignore", category=UserWarning, message="`sklearn.utils.parallel.delayed` should be used with `sklearn.utils.parallel.Parallel`")
from sklearn.utils.class_weight import compute_class_weight


param_grid = {
    'balancedrandomforestclassifier__n_estimators': sp_randint(500, 700),
    'balancedrandomforestclassifier__max_depth': list(range(30, 41)),
    'balancedrandomforestclassifier__min_samples_split': [2, 3, 4],
    'balancedrandomforestclassifier__min_samples_leaf': [1, 2, 3],
    'balancedrandomforestclassifier__max_features': list(np.arange(0.3, 0.6, 0.05)),
    'balancedrandomforestclassifier__criterion': ['gini', 'entropy'],
    'balancedrandomforestclassifier__bootstrap': [True, False]
}
# Compute class weights on the full training set or a large enough sample
sample_size = min(len(y_train), 10000)  # Adjust the sample size as needed
sample_indices = np.random.choice(len(y_train), size=sample_size, replace=False)
sample_y = y_train[sample_indices]

class_weights = compute_class_weight("balanced", classes=np.unique(sample_y), y=sample_y)
class_weight_dict = dict(zip(np.unique(sample_y), class_weights))

# Create the pipeline
pipeline = make_pipeline(
    BalancedRandomForestClassifier(random_state=42, class_weight=class_weight_dict, warm_start=True, bootstrap=False, replacement=True)
)

# Initialize the number of iterations and data size
n_iter = 50
data_size = 10000

# Create the StratifiedKFold object
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)


# Set scoring metrics
scoring = {
    'precision': 'precision',
    'recall': 'recall',
    'f1': 'f1',
    'roc_auc': 'roc_auc'
}

# Iterate and narrow down the grid
for _ in range(3):  # Number of iterations to narrow down the grid
    # Sample a subset of data for the current iteration
    idx = np.random.choice(X_train.shape[0], size=data_size, replace=False)
    X_subset = X_train[idx]
    y_subset = y_train[idx]

    # Create the RandomizedSearchCV object
    random_search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=param_grid,
        n_iter=n_iter,
        cv=skf,
        scoring=scoring,
        refit='f1',
        n_jobs=1,
        random_state=42,
        verbose=1
    )

    # Fit the RandomizedSearchCV object on the subset of data
    random_search.fit(X_subset, y_subset)

    # Get the best parameters and best score for the current iteration
    best_params = random_search.best_params_
    best_score = random_search.best_score_
    best_estimator = random_search.best_estimator_

    print(f"Iteration best parameters: {best_params}")
    print(f"Iteration best score: {best_score}")
    print(f"Iteration best estimator: {best_estimator}")

    # Update the parameter grid based on the best parameters
    if isinstance(best_params['balancedrandomforestclassifier__max_features'], str):
      max_features_values = ['sqrt', 'log2', None]
    else:
      max_features_values = list(np.arange(max(0.1, float(best_params['balancedrandomforestclassifier__max_features']) - 0.2), min(1.0, float(best_params['balancedrandomforestclassifier__max_features']) + 0.2), 0.1))

      # Update the parameter grid based on the best parameters
    param_grid = {
      'balancedrandomforestclassifier__n_estimators': sp_randint(500, 700),
      'balancedrandomforestclassifier__max_depth': list(range(30, 41)),
      'balancedrandomforestclassifier__min_samples_split': [2, 3, 4],
      'balancedrandomforestclassifier__min_samples_leaf': [1, 2, 3],
      'balancedrandomforestclassifier__max_features': list(np.arange(0.3, 0.6, 0.05)),
      'balancedrandomforestclassifier__criterion': ['gini', 'entropy'],
      'balancedrandomforestclassifier__bootstrap': [True, False]
      }

    # Increase the data size for the next iteration
    data_size *= 2

# Get the overall best parameters and best score
best_params = random_search.best_params_
best_score = random_search.best_score_
best_estimator = random_search.best_estimator_
print("Overall best parameters: ", best_params)
print("Overall best score: ", best_score)
print("Overall best estimator: ", best_estimator)

from sklearn.utils.parallel import delayed, Parallel
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, message="Function delayed is deprecated")
warnings.filterwarnings("ignore", category=UserWarning, message="`sklearn.utils.parallel.delayed` should be used with `sklearn.utils.parallel.Parallel`")
from sklearn.utils.class_weight import compute_class_weight



# Initialize the classifier with the best parameters
brfc = BalancedRandomForestClassifier(
    n_estimators=592,
    max_depth=36,
    min_samples_split=2,
    min_samples_leaf=1,
    max_features=0.4,
    bootstrap=False,
    replacement=True,
    criterion='entropy',
    sampling_strategy='all',
    class_weight={0: 0.703037120359955, 1: 1.7313019390581716},
    random_state=42,
    verbose=2,
    n_jobs=2
)

# Fit the classifier to the training data
brfc.fit(X_train, y_train)

# Evaluate the classifier on the test data
score = brfc.score(X_test, y_test)
print(f"Model accuracy on test data: {score}")

# Print all available attributes and methods for the random_search object
all_attributes_methods = dir(random_search)

# Filter out attributes and methods inherited from BaseSearchCV
specific_attributes_methods = [
    attribute for attribute in all_attributes_methods
    if attribute not in dir(RandomizedSearchCV)
]

print("Attributes and methods specific to GridSearchCV:")
for attr in specific_attributes_methods:
    print(attr)

def is_fitted(estimator):
    try:
        getattr(estimator, "estimator")
        return True
    except AttributeError:
        return False

print(is_fitted(brfc))

random_search.score



# Get the best parameters and the corresponding score
best_params = brfc.best_params_
best_score = brfc.best_score_

best_estimator = brfc.best_estimator_

cv_results = brfc.cv_results_

cv_results_df = pd.DataFrame(brfc.cv_results_)

scorer = brfc.scorer_

refit_time = brfc.refit_time_

print("Best parameters:", best_params)
print("Best cross-validation score:", best_score)
print("Best estimator:", best_estimator)
print("CV Results:",cv_results_df)
print("Scorer function:", scorer)
print("Refit time (seconds):", refit_time)

best_model = random_search.best_estimator_

f1_score?

# Predictions for test data
y_pred = brfc.predict(X_test)

# Calculate accuracy
accuracy = accuracy_score(y_test, y_pred)
print("Accuracy:", accuracy)

# Calculate F1-score (use 'weighted' or 'macro' depending on your problem)
f1 = f1_score(y_test, y_pred, average='weighted')
print("F1-score:", f1)

# Print classification report
report = classification_report(y_test, y_pred)
print("Classification report:\n", report)

f1_score?

ConfusionMatrixDisplay.from_predictions(y_test, y_pred)
plt.show()

# Predictions for train data
y_pred_train = brfc.predict(X_train)

# Confusion matrix and classification report for train data
train_cm = confusion_matrix(y_train, y_pred_train)
train_cr = classification_report(y_train, y_pred_train)
print("Training confusion matrix:")
print(train_cm)
print("Training classification report:")
print(train_cr)

disp = ConfusionMatrixDisplay.from_estimator(
        brfc,
        X_test,
        y_test,
        cmap=plt.cm.Blues)

title = disp.ax_.set_title("Confusion matrix")

print(title)
print(disp.confusion_matrix)

plt.show()

#Calculate feature importances and the standard deviation for those importances
importances = brfc.feature_importances_
std = np.std([tree.feature_importances_ for tree in brfc.estimators_], axis=0)


 # list of feature names corresponding to the input bands of your raster stack
feature_names =  [ 'CITIES','GRUPO', 'PORTS', 'PRECIPITATION', 'RIVER','ROAD','SOIL'  ]
# Create a sorted list of tuples containing feature names and their importances:
sorted_features = sorted(zip(feature_names, importances, std), key=lambda x: x[1], reverse=True)

# Create a bar chart
fig, ax = plt.subplots()

# Set the feature names as x-axis labels
ax.set_xticklabels([item[0] for item in sorted_features], rotation=45, ha='right')
ax.set_xticks(range(len(sorted_features)))

# Set the y-axis labels as importances
ax.bar(range(len(sorted_features)), [item[1] for item in sorted_features], yerr=[item[2] for item in sorted_features])

# Set the title and labels for the chart
ax.set_title('Feature Importances')
ax.set_xlabel('Features')
ax.set_ylabel('Importance')

# Display the chart
plt.tight_layout()
plt.show()

# Assuming you have trained your model and obtained the feature importances
importances = brfc.feature_importances_

# Get the indices of the GRUPO-related binary features
grupo_indices = [i for i, feature in enumerate(feature_names) if 'GRUPO' in feature]

# Calculate the aggregated importance score for the GRUPO feature
grupo_importance = np.sum(importances[grupo_indices])

# Create a new list of feature names with GRUPO as a single feature
aggregated_feature_names = [feature for feature in feature_names if 'GRUPO' not in feature]
aggregated_feature_names.append('GRUPO')

# Create a new list of importances with the aggregated GRUPO importance
aggregated_importances = [imp for i, imp in enumerate(importances) if i not in grupo_indices]
aggregated_importances.append(grupo_importance)

# Create a sorted list of tuples containing aggregated feature names and their importances
sorted_features = sorted(zip(aggregated_feature_names, aggregated_importances), key=lambda x: x[1], reverse=True)

# Visualize the aggregated feature importances
fig, ax = plt.subplots()
ax.set_xticklabels([item[0] for item in sorted_features], rotation=45, ha='right')
ax.set_xticks(range(len(sorted_features)))
ax.bar(range(len(sorted_features)), [item[1] for item in sorted_features])
ax.set_title('Aggregated Feature Importances')
ax.set_xlabel('Features')
ax.set_ylabel('Importance')
plt.tight_layout()
plt.show()

feature_groups = [['CITIES'], ['PORTS'], ['PRECIPITATION'], ['RIVER'], ['ROAD'], ['SOIL']]
grupo_features = [feature for feature in feature_names if 'GRUPO' in feature]
feature_groups.append(grupo_features)

from sklearn.inspection import permutation_importance

# Assuming you have your trained model (brfc) and the preprocessed input data (X_test, y_test)

# Convert X_test to a dense numpy array
X_test_dense = X_test.toarray()

# Initialize a dictionary to store the permutation importances for each feature group
perm_importances = {}

# Iterate over each feature group
for group in feature_groups:
    # Calculate the permutation importance for all features
    perm_importance = permutation_importance(brfc, X_test_dense, y_test, n_repeats=10, random_state=42)

    # Create a boolean mask for the current feature group
    mask = [feature in group for feature in feature_names]
    mask = np.array(mask)
    # Set the importance of non-group features to zero
    perm_importance.importances_mean[~mask] = 0
    perm_importance.importances_std[~mask] = 0

    # Store the mean and standard deviation of the permutation importance scores
    perm_importances[group[0] if len(group) == 1 else 'GRUPO'] = (perm_importance.importances_mean.sum(),
                                                                  perm_importance.importances_std.sum())

# Create a sorted list of tuples containing feature group names and their importances
sorted_grouped_features = sorted(perm_importances.items(), key=lambda x: x[1][0], reverse=True)

# Visualize the grouped feature importances
fig, ax = plt.subplots(figsize=(8, 6))
ax.set_xticklabels([item[0] for item in sorted_grouped_features], rotation=45, ha='right')
ax.set_xticks(range(len(sorted_grouped_features)))
ax.bar(range(len(sorted_grouped_features)), [item[1][0] for item in sorted_grouped_features],
       yerr=[item[1][1] for item in sorted_grouped_features])
ax.set_title('Grouped Feature Importances')
ax.set_xlabel('Feature Groups')
ax.set_ylabel('Permutation Importance')
plt.tight_layout()
plt.show()

#AREA_AUTORIZADA: 1 BOSQUES: 2 EN_CONFLICTO: 3 OTRAS_COBERTURAS: 4 OTRAS_TIERRAS_FORESTALES: 5 unclassified: 6

# List of feature names corresponding to the input raster stack
feature_names = ['CITIES', 'GRUPO_1', 'GRUPO_2', 'GRUPO_3', 'GRUPO_4', 'GRUPO_5', 'GRUPO_6',
                 'PORTS', 'PRECIPITATION', 'RIVER', 'ROAD',
                 'SOIL_1', 'SOIL_2', 'SOIL_3', 'SOIL_4', 'SOIL_5', 'SOIL_6', 'SOIL_7',
                 'SOIL_8', 'SOIL_9', 'SOIL_10', 'SOIL_11', 'SOIL_12', 'SOIL_13',
                 'SOIL_14', 'SOIL_15', 'SOIL_16']
# Calculate feature importances and the standard deviation for those importances
importances = brfc.feature_importances_
std = np.std([tree.feature_importances_ for tree in brfc.estimators_], axis=0)

# Create a sorted list of tuples containing feature names and their importances
sorted_features = sorted(zip(feature_names, importances, std), key=lambda x: x[1], reverse=True)

# Create a bar chart
fig, ax = plt.subplots(figsize=(10, 6))

# Set the feature names as x-axis labels
ax.set_xticklabels([item[0] for item in sorted_features], rotation=45, ha='right')
ax.set_xticks(range(len(sorted_features)))

# Set the y-axis labels as importances
ax.bar(range(len(sorted_features)), [item[1] for item in sorted_features],
       yerr=[item[2] for item in sorted_features])

# Set the title and labels for the chart
ax.set_title('Feature Importances')
ax.set_xlabel('Features')
ax.set_ylabel('Importance')

# Display the chart
plt.tight_layout()
plt.show()

#AREA_AUTORIZADA: 1 BOSQUES: 2 EN_CONFLICTO: 3 OTRAS_COBERTURAS: 4 OTRAS_TIERRAS_FORESTALES: 5 unclassified: 6

# List of feature names corresponding to the input raster stack
feature_names = ['CITIES', 'GRUPO_1', 'GRUPO_2', 'GRUPO_3', 'GRUPO_4', 'GRUPO_5', 'GRUPO_6',
                 'PORTS', 'PRECIPITATION', 'RIVER', 'ROAD',
                 'SOIL_1', 'SOIL_2', 'SOIL_3', 'SOIL_4', 'SOIL_5', 'SOIL_6', 'SOIL_7',
                 'SOIL_8', 'SOIL_9', 'SOIL_10', 'SOIL_11', 'SOIL_12', 'SOIL_13',
                 'SOIL_14', 'SOIL_15', 'SOIL_16']
# Calculate feature importances and the standard deviation for those importances
importances = brfc.feature_importances_
std = np.std([tree.feature_importances_ for tree in brfc.estimators_], axis=0)

# Create a sorted list of tuples containing feature names and their importances
sorted_features = sorted(zip(feature_names, importances, std), key=lambda x: x[1], reverse=True)

# Create a bar chart
fig, ax = plt.subplots(figsize=(10, 6))

# Set the feature names as x-axis labels
ax.set_xticklabels([item[0] for item in sorted_features], rotation=45, ha='right')
ax.set_xticks(range(len(sorted_features)))

# Set the y-axis labels as importances
ax.bar(range(len(sorted_features)), [item[1] for item in sorted_features],
       yerr=[item[2] for item in sorted_features])

# Set the title and labels for the chart
ax.set_title('Feature Importances')
ax.set_xlabel('Features')
ax.set_ylabel('Importance')

# Display the chart
plt.tight_layout()
plt.show()

y_pred_prob = brfc.predict_proba(X_test)[:, 1]

print("Shape of y_proba_curve:", y_pred_prob.shape)

#Assuming you have the true labels (y_test) and predicted probabilities (y_pred_prob)
precision, recall, thresholds = precision_recall_curve(y_test, y_pred_prob)

# Plot the precision-recall curve
plt.figure(figsize=(8, 6))

plt.plot(recall, precision, marker='.', label='Precision-Recall Curve')
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve')
plt.legend(loc='lower left')
plt.grid()
plt.show()

print(f"Area under Precision-Recall curve: {auc(recall, precision)}")

# Assuming you have the true labels (y_test) and predicted probabilities (y_pred_prob)
fpr, tpr, thresholds = roc_curve(y_test, y_pred_prob)

# Calculate the Area Under the Curve (AUC)
roc_auc = auc(fpr, tpr)

# Plot the ROC curve
plt.figure(figsize=(8, 6))
plt.plot(fpr, tpr, color='blue', lw=2, label=f'ROC curve (AUC = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], color='red', lw=2, linestyle='--', label='Random guess')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic (ROC) Curve')
plt.legend(loc="lower right")
plt.grid()
plt.show()

print(f"Area under ROC curve: {auc(fpr, tpr)}")

# Predict probabilities for deforestation events
y_proba = brfc.predict_proba(X_cleaned)[:, 1]

# Predicts the
# Create a probability raster by filling in the valid pixel values
prob_raster = np.full(y.shape, no_data_value, dtype=np.float32)
prob_raster[valid_rows] = y_proba
prob_raster = prob_raster.reshape(feature_data_arrays[0].shape)

print(y_proba.shape)

try:
    joblib.dump(best_params, 'best_params.pkl')
    joblib.dump(best_score, 'best_score.pkl')
    joblib.dump(best_model, 'best_model.pkl')
    joblib.dump(cv_results, 'cv_results.pkl')
    joblib.dump(cv_results_df, 'cv_results_df.pkl')
    joblib.dump(scorer, 'scorer.pkl')
    joblib.dump(refit_time, 'refit_time.pkl')
    joblib.dump(report, 'report.pkl')
except Exception as e:
    print(f"An error occurred: {e}")

# Save the probability raster as a GeoTIFF file
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

output_file = os.path.join(output_folder, "brfc-df-prediction-feature.tiff")

with rasterio.open(y_file) as src:
    profile = src.profile
    profile.update(dtype=rasterio.float32, count=1)

prob_raster_reshaped = prob_raster.reshape((1, prob_raster.shape[0], prob_raster.shape[1]))

with rasterio.open(output_file, 'w', **profile) as dst:
    dst.write_band(1, prob_raster_reshaped[0])

# Report
model_report = f'''

Balanced Random Forest Classifier Model Report

# Summary

The Balanced Random Forest Classifier performed reasonably well on this task,
with an accuracy of  {accuracy} and an F1-score of {f1}.
However, there is room for improvement, particularly in the precision and recall for class 1.
Future work could explore different models, additional feature engineering, or further hyperparameter tuning to improve performance.

# Model Selection

We chose to use a Balanced Random Forest Classifier for this task.
This model is an ensemble method that combines the predictions of several base estimators
built with a given learning algorithm in order to improve generalizability and robustness over a single estimator.
It also handles imbalanced classes, which is a common problem in many machine learning tasks.

Hyperparameter Tuning
We used RandomizedSearchCV for hyperparameter tuning.
This method performs a random search on hyperparameters, which is more efficient than an exhaustive search like GridSearchCV.

The hyperparameters we tuned were:

'n_estimators': The number of trees in the forest.
'max_depth': The maximum depth of the tree.
'min_samples_split': The minimum number of samples required to split a node.
'min_samples_leaf': The minimum number of samples required at a leaf node.
'bootstrap': Whether bootstrap samples are used when building trees.

{param_grid}

# Model Performance
The best parameters found by RandomizedSearchCV were:

Best parameters:, {best_params}



With these parameters, the model achieved the following performance metrics:
Best cross-validation score: {best_score}
Best model:, {best_estimator}
Scorer function:, {scorer}
Refit time (seconds): {refit_time}
Accuracy:, {accuracy}
F1-score: {f1}

# Testing Data

Classification report:

{report}

#  TRAINING DATA Classificatin Report-Confusion Matrix

Training confusion matrix:

{train_cm}

Training classification report:

{train_cr}


This indicates that the model correctly classified [1,1] instances of class 0
and [2,2] instances of class 1,

while misclassifying [1,2] instances of class 0 and [2,1] instances of class 1.

CV Results:
{cv_results_df}

'''
# Write the report to a Quarto markdown file
with open('model_report.qmd', 'w') as f:
    f.write(model_report)