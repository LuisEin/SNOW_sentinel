# -*- coding: utf-8 -*-

'''
Created on Monday Jul 15 12:46:12 2024

This script loads processed Sentinel data tif files with three classes
255 - noData - nan
1 - wetsnow
0 - Dry snow or snow free or patchy snow

Creates maps to see the wet snow patterns

Further this script takes SWS files, with more classes and plots them
@author: luis
'''
from functions_sentinel import process_directory



# Specify the input directory containing TIF files
input_directory = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/SWS/SWS_all_data_processed/binary_1wet_0dry'
# Specify the output directory to save the plots
output_directory = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/SWS/SWS_analytics/SWS_maps'

# If you want to process binary data use True
use_binary = True
process_directory(input_directory, output_directory, use_binary)


# All the classes:
# Specify the input directory containing TIF files
input_directory = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/SWS/SWS_all_data_processed/all_classes'
# Specify the output directory to save the plots
output_directory = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/SWS/SWS_analytics/SWS_maps/all_classes'

# Set use_binary to False if you want to the all_classes tif files 
use_binary = False
process_directory(input_directory, output_directory, use_binary)