#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 15 22:29:58 2024

@author: luis
"""

from osgeo import gdal

def get_image_dimensions(file_path):
    # Open the dataset
    dataset = gdal.Open(file_path)
    if not dataset:
        raise FileNotFoundError(f"Unable to open file: {file_path}")

    # Get the dimensions
    width = dataset.RasterXSize
    height = dataset.RasterYSize

    # Close the dataset
    dataset = None

    return width, height

# Example usage
file_path = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/PlanetScope_Data/Data_March-June_23_Feb-March_24_psscene_analytic_sr_udm2/PSScene/20230301_094551_90_247a_3B_AnalyticMS_SR_clip.tif'
width, height = get_image_dimensions(file_path)
print(f"Width: {width} pixels, Height: {height} pixels")
