# -*- coding: utf-8 -*-
"""tfdf1ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ghg7-pTM1l9K6CRzFnTirqUu-IwUcav-
"""

!pip install tensorflow_decision_forests wurlitzer

!pip install rasterio

from google.colab import drive
drive.mount('/content/drive')

import tensorflow_decision_forests as tfdf

import os
import numpy as np
import pandas as pd
import tensorflow as tf
import math

from IPython.core.magic import register_line_magic
from IPython.display import Javascript
from IPython.display import display as ipy_display

import rasterio
import pandas as pd
from sklearn.model_selection import train_test_split

# Some of the model training logs can cover the full
# screen if not compressed to a smaller viewport.
# This magic allows setting a max height for a cell.
@register_line_magic
def set_cell_height(size):
  ipy_display(
      Javascript("google.colab.output.setIframeHeight(0, true, {maxHeight: " +
                 str(size) + "})"))

# Check the version of TensorFlow Decision Forests
print("Found TensorFlow Decision Forests v" + tfdf.__version__)

grupo_path = '/content/drive/MyDrive/data/output_grupo_raster.tif'
binary_path = '/content/drive/MyDrive/data/binary_deforestation_raster.tif'

# Load the raster data
with rasterio.open(grupo_path) as src:
    feature_raster = src.read(1)

with rasterio.open(binary_path) as src:
    label_raster = src.read(1)

# Flatten the raster arrays and create a DataFrame
pixels = {'feature': feature_raster.flatten(),
          'label': label_raster.flatten()}
df = pd.DataFrame(pixels)

# Remove nodata pixels (assuming nodata is -1 for label)
df = df[df['label'] != -1]

# Split the data into training and testing sets
train_df, test_df = train_test_split(df, test_size=0.3)

del df
del pixels

# Convert DataFrame to TensorFlow dataset
train_ds = tfdf.keras.pd_dataframe_to_tf_dataset(train_df, label='label')
test_ds = tfdf.keras.pd_dataframe_to_tf_dataset(test_df, label='label')

# Train a Random Forest model
model = tfdf.keras.RandomForestModel()
model.fit(train_ds)

# Evaluate the model
evaluation = model.evaluate(test_ds)

print(evaluation)

model.compile(metrics=["accuracy"])
evaluation = model.evaluate(test_ds, return_dict=True)
print()

for name, value in evaluation.items():
  print(f"{name}: {value:.4f}")

tfdf.model_plotter.plot_model_in_colab(model, tree_idx=0, max_depth=3)

# Commented out IPython magic to ensure Python compatibility.
# %set_cell_height 300
model.summary()

"""Accuracy: The OOB accuracy of 0.707625 suggests that about 70.76% of the OOB samples were correctly classified by the model.
Logloss: The logarithmic loss (logloss) of 10.5383 is a measure of error and is more sensitive to classifiers that are confident about an incorrect classification.
OOB evaluation is a method of measuring the prediction error of random forest models. For each tree, it uses only the data that was not included in the bootstrap sample (the "out-of-bag" data) to evaluate the model's performance. This provides a good estimate of how well the model might perform on unseen data.
"""

# The input features
model.make_inspector().features()

# The feature importances
model.make_inspector().variable_importances()

model.make_inspector().evaluation()

# Commented out IPython magic to ensure Python compatibility.
# %set_cell_height 150
model.make_inspector().training_logs()

import matplotlib.pyplot as plt

logs = model.make_inspector().training_logs()

plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.plot([log.num_trees for log in logs], [log.evaluation.accuracy for log in logs])
plt.xlabel("Number of trees")
plt.ylabel("Accuracy (out-of-bag)")

plt.subplot(1, 2, 2)
plt.plot([log.num_trees for log in logs], [log.evaluation.loss for log in logs])
plt.xlabel("Number of trees")
plt.ylabel("Logloss (out-of-bag)")

plt.show()

# Commented out IPython magic to ensure Python compatibility.
# This cell start TensorBoard that can be slow.
# Load the TensorBoard notebook extension
# %load_ext tensorboard
# Google internal version
# %load_ext google3.learning.brain.tensorboard.notebook.extension

# Clear existing results (if any)
!rm -fr "/tmp/tensorboard_logs"

# Export the meta-data to tensorboard.
model.make_inspector().export_to_tensorboard("/tmp/tensorboard_logs")

# Commented out IPython magic to ensure Python compatibility.
# docs_infra: no_execute
# Start a tensorboard instance.
# %tensorboard --logdir "/tmp/tensorboard_logs"

?tfdf.keras.RandomForestModel

predictions = model.predict(test_ds)
predicted_labels = np.argmax(predictions, axis=1)

# Extract the true labels from the test DataFrame
true_labels = test_df['label'].values

from sklearn.metrics import confusion_matrix

# Assuming 'true_labels' contains the true labels from your test dataset
conf_matrix = confusion_matrix(true_labels, predicted_labels)
print(conf_matrix)

"""Out-of-Bag (OOB) Evaluation:
OOB evaluation is a method used in random forests to estimate the model's performance. In random forests, each tree is trained on a different bootstrap sample from the training data. Some instances are left out of the bootstrap sample and not used in training a particular tree. These left-out instances are called "out-of-bag" for that tree.

How OOB Works: For each instance in the training dataset, the model predicts its class using only the trees for which this instance was out-of-bag. This process is akin to cross-validation and provides an unbiased estimate of the model's performance.
OOB Metrics: Common OOB metrics include accuracy and logloss. They give an idea of how well the model is expected to perform on unseen data.
OOB in Your Model:
Accuracy: An OOB accuracy of around 70.76% was observed, suggesting that the model correctly classified approximately 70.76% of the OOB instances.
Logloss: The logloss was around 10.5383, a measure of error where lower values are better.
Note:
OOB evaluation is a handy feature of random forests as it provides an estimate of model performance without needing a separate validation set.
However, OOB evaluation alone might not always capture the model's behavior on highly imbalanced datasets or specific data distributions. It's always good to complement it with other evaluation methods, like the confusion matrix on a separate test set.
"""
