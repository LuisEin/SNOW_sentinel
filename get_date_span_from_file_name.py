#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 11:20:55 2024

@author: luis
"""
import os
from datetime import datetime

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

def sort_dates_into_spans(dates, span_days=7):
    # Sort the dates
    dates.sort()
    spans = []
    current_span = []

    for date in dates:
        if not current_span:
            current_span.append(date)
        else:
            # Check if the current date is within the span_days range from the first date in the current span
            if (date - current_span[0]).days <= span_days:
                current_span.append(date)
            else:
                spans.append([current_span[0], current_span[-1]])
                current_span = [date]

    if current_span:
        spans.append([current_span[0], current_span[-1]])

    return spans

def main(folder_path):
    # Get dates from filenames
    dates = get_dates_from_filenames(folder_path)
    # Sort dates into spans of no more than span_days days
    date_spans = sort_dates_into_spans(dates)
    
    # Print the date spans
    for i, span in enumerate(date_spans):
        print(f"Span {i+1}: {[date.strftime('%Y-%m-%d') for date in span]}")

    return date_spans

# Example usage:
folder_path = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/PlanetScope_Data/Data_March-June_23_Feb-March_24_psscene_analytic_sr_udm2/PSScene'
date_spans = main(folder_path)

# date_spans now contains the sorted date spans as a list of lists of datetime objects
print(f"Distinct date spans: {[[date.strftime('%Y-%m-%d') for date in span] for span in date_spans]}")
