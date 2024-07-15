# -*- coding: utf-8 -*-
'''
Created on Tuesday Jul 14 15:02:12 2024

This script takes Sentinel SWS data in a directory in this format: 
    SWS_20180101T170648_S1A_T32TPT_V101_1.zip
It unzips the files, opens the geotiff, crops it to the AOI,
Calulates mean and sum of wet snow pixels and saves it to a df
Saves the newly created geotiffs to a directory
@author: luis
'''

import os
import glob
import zipfile
from functions_sentinel import * 
from osgeo import gdal
from datetime import datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Define paths for data folder, AOI shapefile, mask file, temporary directory, log file, and output folder
data_folder = "/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/SWS/SWS_raw_files"
aoi_path = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Shapefiles/shapefile_Zugspitze/03_AOI_shp_zugspitze_reproj_for_code/AOI_zugspitze_reproj_32632.shp' #/shapefile_new_approach/mask_catchments_32632.asc
mask_file_path = "/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Shapefiles/shapefile_Zugspitze/04_AOI_shapefile_Zugspitze_Watershed/shapefile_new_approach/mask_catchments_32632.asc"
local_temp = "/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/code/temp"
log_path = "/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/code/logfile.txt"
# Path to df_datestamp where wetsnow sums and means are saved
analytic_path = "/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/SWS/SWS_analytics"
output_folder = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/SWS/SWS_all_data_processed/all_classes'

### Main Processing
# Create a dataframe from the directory of zip files
scenes_df = df_from_dir(data_folder)
grouped = scenes_df.groupby(["sensdate"])
days = scenes_df["sensdate"].unique()
# get bounds from shapefile
bounds_aoi = getBounds_Shp(aoi_path)
# get bounds from ASCII grid
# bounds_aoi = get_bounds_from_mask(mask_file_path)
# Initialize dataframe to store results
df_datestamp = pd.DataFrame(index=pd.Index(days, name='Date'))
df_datestamp["wetsnow_mean"] = np.nan
df_datestamp["wetsnow_sum"] = np.nan

# iterate through days
for day in days:
    # Clear the temporary directory before processing each day
    clear_temp_directory(local_temp)
    group = grouped.get_group((day,))
    mean_datetime = str(group.sensdatetime.mean())
    print("processing {} with {} scenes".format(str(day)[0:10], group.shape[0]))

    # Define output file path
    outfile = "{}{}SWS_{}_{}.tif".format(
        output_folder,
        os.path.sep,
        mean_datetime[0:10].replace("-", "_"),
        mean_datetime[11:16].replace(":", "_"),
    )

    # Check if the output file already exists
    if os.path.isfile(outfile):
        print("File {} already exists, skipping processing!".format(os.path.basename(outfile)))
        continue

    # Extract files from zip archives
    for i, scene_name in enumerate(group["filename"]):
        zipfilepath = "{}{}{}.zip".format(data_folder, os.path.sep, scene_name)
        fileoutpath = "{}{}{}.tif".format(local_temp, os.path.sep, scene_name)

        try:
            with zipfile.ZipFile(zipfilepath) as z:
                with open(fileoutpath, "wb") as f:
                    f.write(z.read("{}/{}_WSM.tif".format(scene_name, scene_name)))
        except Exception as e:
            writeLog(log_path, "Couldnt unzip file {} for folowing reason: {}".format(e, zipfilepath))

    # Find the unzipped tif files
    scenes = glob.glob("{}{}SWS*.tif".format(local_temp, os.path.sep))

    # Iterate through each tif file
    for scene in scenes:
        # readraster
        rasterarray, scene_geotrans, projection, bounds = readRaster(scene)
        rasterarray = rasterarray

        # get some infos from topo geotrans
        scene_min_x = scene_geotrans[0]
        scene_min_y = scene_geotrans[3]
        scene_res = scene_geotrans[1]
        # create topo_params list for clipping
        scene_params = [scene_min_x, scene_min_y, scene_res]

        # clip raster 
        data_aoi, geotrans_aoi = clipArray(rasterarray, scene_params, bounds_aoi, log_path)
        # Extract the date from the filename
        scene_filename = os.path.basename(scene)
        date_str = scene_filename.split("_")[1]
        current_date = dt.strptime(date_str, "%Y%m%dT%H%M%S")

        # Skip processing if the data contains only NaN values
        if np.all(data_aoi == 255):
            print(f"Skipping and removing scene {scene} as it contains only NaN values.")
            # Remove the corresponding date from the DataFrame
            if current_date in df_datestamp.index:
                df_datestamp = df_datestamp.drop(current_date)
            else:
                print(f"{current_date} not found in DataFrame index, skipping drop.")
            continue

        # # replace specific values in the clipped data
        # # Set unwanted classes na and wet and dry snow to binary
        # data_aoi[data_aoi == 110] = 1
        # # Dry snow or snow free or patchy snow
        # data_aoi[data_aoi == 125] = 0
        # # Radar shadow / layover / foreshortening
        # data_aoi[data_aoi == 200] = 255
        # # Water
        # data_aoi[data_aoi == 210] = 255
        # # Forest
        # data_aoi[data_aoi == 220] = 255
        # # Urban area
        # data_aoi[data_aoi == 230] = 255
        # # Non-mountain areas
        # data_aoi[data_aoi == 240] = 255

        # replace specific values in the clipped data
        # Set unwanted classes na and wet and dry snow to binary
        data_aoi[data_aoi == 110] = 1
        # Dry snow or snow free or patchy snow
        data_aoi[data_aoi == 125] = 0
        # Radar shadow / layover / foreshortening
        data_aoi[data_aoi == 200] = 21
        # Water
        data_aoi[data_aoi == 210] = 22
        # Forest
        data_aoi[data_aoi == 220] = 23
        # Urban area
        data_aoi[data_aoi == 230] = 24
        # Non-mountain areas
        data_aoi[data_aoi == 240] = 25


        # Calculate mean and sum of wet snow pixels
        meanwetsnowarea = np.nanmean(data_aoi[data_aoi != 255])
        sumwetsnowpixels = np.nansum(data_aoi[data_aoi != 255])

        print("meanwetsnowpart of scene is: {}".format(meanwetsnowarea))
        print("wetsnowsum of scene is: {}".format(sumwetsnowpixels))

        # Write the clipped data to a grid file if valid
        if not np.isnan(meanwetsnowarea and sumwetsnowpixels):
            write_grid(outfile, data_aoi, geotrans_aoi, projection, log_path, dtype=gdal.GDT_Byte)

        # Store results in the dataframe
        df_datestamp.loc[current_date, 'wetsnow_mean'] = meanwetsnowarea
        df_datestamp.loc[current_date, 'wetsnow_sum'] = sumwetsnowpixels

    # Clear the temporary directory after processing each day
    clear_temp_directory(local_temp)
    
    
# After creating df_datestamp, save it to analytic_path
df_datestamp_path = os.path.join(analytic_path, "df_datestamp.csv")
df_datestamp.to_csv(df_datestamp_path, index=True)
print(f"DataFrame saved to {df_datestamp_path}")

## short plot
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