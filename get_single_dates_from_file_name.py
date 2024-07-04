#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 11:20:55 2024

@author: luis
"""
import os
from datetime import datetime
import numpy as np
import pandas as pd

def get_dates_from_filenames(folder_path):
    filenames = os.listdir(folder_path)
    dates = []

    for filename in filenames:
        try:
            # Extract the date part from the filename
            date_str = filename.split('_')[0]
            # Convert the date string to a datetime object
            date = datetime.strptime(date_str, "%Y%m%d")
            dates.append(date)
        except ValueError:
            # Handle the case where the date is not in the expected format
            print(f"Filename {filename} does not have the expected date format.")

    return dates

def main(folder_path):
    # Get dates from filenames
    dates = get_dates_from_filenames(folder_path)
    
    # Convert dates to numpy array
    dates_array = np.array(dates)
    
    # Create a pandas DataFrame
    dates_df = pd.DataFrame(dates_array, columns=['Date'])
    
    # Print the DataFrame
    print(dates_df)
    
    return dates_df


# Example usage:
folder_path = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/PlanetScope_Data/Data_March-June_23_Feb-March_24_psscene_analytic_sr_udm2/PSScene'
date_spans = main(folder_path)


