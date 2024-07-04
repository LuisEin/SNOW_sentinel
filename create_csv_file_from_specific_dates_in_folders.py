#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 12:01:56 2024

This code uses the calculated Indices folders
NDVI, GST, BST
and creates a .CSV file with the regarding dates and 
empty columns regarding the indices

@author: luis
"""

import os
import re
import csv
from datetime import datetime


# Function to extract date and time from filename using regex
def extract_datetime(filename):
    # Adjust the regex pattern to match the date and time format in your filenames
    pattern = r'(\d{8})_(\d{6})'  # Matches YYYYMMDD_HHMMSS
    match = re.search(pattern, filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        datetime_str = f"{date_str}_{time_str}"
        return datetime.strptime(datetime_str, '%Y%m%d_%H%M%S')
    else:
        return None

# Function to read datetimes from files in a directory
def read_datetimes_from_folder(folder_path):
    datetimes = []
    for filename in os.listdir(folder_path):
        datetime_obj = extract_datetime(filename)
        if datetime_obj:
            datetimes.append(datetime_obj)
    return datetimes

# Function to find unique dates across all folders
def find_unique_dates(folder_paths):
    unique_dates = set()
    for folder_path in folder_paths:
        dates_in_folder = read_datetimes_from_folder(folder_path)
        unique_dates.update(dates_in_folder)
    return list(unique_dates)

# Function to write unique dates to CSV
def write_to_csv(unique_dates, csv_filename):
    headers = ['Date', 'NDVI-Threshold', 'GST-Threshold', 'BST-Threshold', 'Cloudfree', 'Comments']
    rows = [[date, '', '', '', '', ''] for date in unique_dates]
    with open(csv_filename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(headers)
        csvwriter.writerows(rows)
    print(f"CSV file '{csv_filename}' created successfully.")

# Main function
def main():
    # Replace with your actual folder paths
    folder_paths = [
        '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/PlanetScope_Data/Indices/BST',
        '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/PlanetScope_Data/Indices/GST',
        '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/PlanetScope_Data/Indices/NDVI'
    ]
    
    # Find unique dates across all folders
    unique_dates = find_unique_dates(folder_paths)
    
    # Write unique dates to CSV file
    csv_filename = 'unique_dates.csv'
    write_to_csv(unique_dates, csv_filename)

if __name__ == "__main__":
    main()