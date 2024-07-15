# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt


# Define the path to the CSV file
path_to_file = "/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/SWS/SWS_analytics/df_datestamp_20180101_to_20240622.csv"


# Load the DataFrame
df_datestamp = pd.read_csv(path_to_file)


# Convert the 'date' column to datetime type
df_datestamp['Date'] = pd.to_datetime(df_datestamp['Date'])

# Set the 'date' column as the index
df_datestamp.set_index('Date', inplace=True)

# Plotting mean of wet snow
plt.figure(figsize=(10, 6))
plt.plot(df_datestamp.index, df_datestamp['wetsnow_mean'], marker='o', linestyle='', color='blue')
plt.title('Mean proportion of Wetsnow Pixels Over Time')
plt.xlabel('Date')
plt.ylabel('Mean of Wetsnow Pixels')
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Plotting total sum of wet snow pixels
plt.figure(figsize=(10, 6))
plt.plot(df_datestamp.index, df_datestamp['wetsnow_sum'], marker='o', linestyle='', color='blue')
plt.title('Total Sum of Wetsnow Pixels Over Time')
plt.xlabel('Date')
plt.ylabel('Sum of Wetsnow Pixels')
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()