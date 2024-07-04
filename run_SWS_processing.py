#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 12:52:47 2024

@author: le

This script takes Sentinel1 SAR Wet Snow data .zip files and
Unzips them
Opens the geotiff  and clips it to the AOI
Calculates the mean and the sum of wetsnow pixels
Saves the clipped file
Saves the mean and sum into a pandas_df with date_index

Depending on if the AOI is defined as a shapefile or ASCII file it needs to be 
changed in the bounds_aoi variable

"""
import os, glob, sys, zipfile, math
from osgeo import gdal, gdalconst, osr, ogr
from datetime import datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


data_folder = "/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/code/temp_1"
# 04_AOI_shapefile_Zugspitze_Watershed or 03_AOI_shp_zugspitze_reproj_for_code
aoi_path = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Shapefiles/shapefile_Zugspitze/03_AOI_shp_zugspitze_reproj_for_code/AOI_zugspitze_reproj_32632.shp' #/shapefile_new_approach/mask_catchments_32632.asc
# This is for an ASCII file
mask_file_path = "/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Shapefiles/shapefile_Zugspitze/04_AOI_shapefile_Zugspitze_Watershed/shapefile_new_approach/mask_catchments_32632.asc"
local_temp = "/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/code/temp_new"
log_path = "/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/code/logfile.txt"
output_folder = '/home/luis/Data/04_Uni/03_Master_Thesis/SNOW/02_data/Sentinel_Data/SWS/SWS_ASCII'


# New function to read the ASCII grid file
def read_ascii_grid(filename):
    with open(filename, 'r') as file:
        header = [file.readline() for _ in range(6)]
    ncols = int(header[0].split()[1])
    nrows = int(header[1].split()[1])
    xllcorner = float(header[2].split()[1])
    yllcorner = float(header[3].split()[1])
    cellsize = float(header[4].split()[1])
    nodata_value = float(header[5].split()[1])
    data = np.loadtxt(filename, skiprows=6)
    return ncols, nrows, xllcorner, yllcorner, cellsize, nodata_value, data

# New function to get bounds from the mask file
def get_bounds_from_mask(mask_file_path):
    ncols, nrows, xllcorner, yllcorner, cellsize, nodata_value, data = read_ascii_grid(mask_file_path)
    xmin = xllcorner
    xmax = xllcorner + ncols * cellsize
    ymin = yllcorner
    ymax = yllcorner + nrows * cellsize
    return [xmin, xmax, ymin, ymax]


def df_from_dir(directory):
    # get zip files from directory and read tilecode and timestamp from
    filelist = glob.glob("{}{}*.zip".format(directory, os.path.sep))

    if not all([os.path.basename(file).startswith("SWS") for file in filelist]):
        print(
            "Not all Zipfiles seem to be FSC products! Check Data Folder! \nAborting Script execution..."
        )
        sys.exit()

    filelist = [
        os.path.basename(file).split(".")[0]
        for file in glob.glob("{}{}*.zip".format(directory, os.path.sep))
    ]

    sens_dates = [dt.strptime(file.split("_")[1], "%Y%m%dT%H%M%S") for file in filelist]
    
    sens_dates.sort()
    
    tiles = [file.split("_")[3] for file in filelist]

    # build DF
    scenes_df = pd.DataFrame(
        {"tilecode": tiles, "sensdatetime": sens_dates, "filename": filelist}
    )

    scenes_df["sensdate"] = scenes_df["sensdatetime"].round("h")

    return scenes_df


def writeLog(logfilepath, string, verbose=True):
    # write error Log to path
    timestring = str(dt.now())[0:19]

    if os.path.isfile(logfilepath):
        with open(logfilepath, "a") as writefile:
            writefile.write("\n{}: {}".format(timestring, string))
        writefile.close()
    else:
        with open(logfilepath, "w") as writefile:
            writefile.write("\n{}: {}".format(timestring, string))
        writefile.close()
    if verbose:
        print(string)



def clipArray(src_data, params, bound, offsetx=0, offsety=0):
    """ usage: clips an array (src_data).
    Takes:
    params = [Xmin_src_arry,Ymax_src_array,Resolution_src_array]
    bound = [minX, maxX, minY, maxY]
    """
    res = params[2]
    srcMinX = params[0]
    srcMaxY = params[1]
    minX = bound[0]
    maxX = bound[1]
    minY = bound[2]
    maxY = bound[3]
    rowMin = int(math.ceil((srcMaxY - minY) / res))
    rowMax = int(round((srcMaxY - maxY) / res))
    colMin = int(round((minX - srcMinX) / res))
    colMax = int(math.ceil((maxX - srcMinX) / res))
    clip = src_data[rowMax + offsety:rowMin + offsety, 
                    colMin + offsetx:colMax + offsetx]
    minXclip = srcMinX + colMin * res
    maxYclip = srcMaxY - rowMax * res
    geoTrans = [minXclip, res, 0, maxYclip, 0, -res]
    return clip, geoTrans


def getBounds_Shp(shapefile):
    shapeData = ogr.Open(shapefile, 0)
    layer = shapeData.GetLayer()
    bounds = layer.GetExtent()
    return bounds

def getBounds_Raster(ds):
    geoTrans = ds.GetGeoTransform()
    width = ds.RasterXSize
    height = ds.RasterYSize
    res = geoTrans[1]
    minX = geoTrans[0]
    maxX = minX + width * res
    maxY = geoTrans[3]
    minY = maxY - height * res
    bounds = [minX, maxX, minY, maxY]
    return bounds

def readRaster(filename):
    ds = gdal.Open(filename)
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray()
    projection = osr.SpatialReference()
    projection.ImportFromWkt(ds.GetProjectionRef())
    geotrans = ds.GetGeoTransform()
    bounds = getBounds_Raster(ds)

    del ds, band
    return data, geotrans, projection, bounds

def getClipParams(ds):
    geoTrans_src = ds.GetGeoTransform()
    res = geoTrans_src[1]
    srcMinX = geoTrans_src[0]
    srcMaxY = geoTrans_src[3]
    params = [srcMinX, srcMaxY, res]
    return params

def write_grid(filename, data, geotrans, projection, driver="GTiff", dtype=None):

    if dtype is None:
        dtype = gdalconst.GDT_Float32

    ds = gdal.GetDriverByName(driver).Create(
        filename, data.shape[1], data.shape[0], 1, dtype, ["COMPRESS=LZW"]
    )
    ds.SetGeoTransform(geotrans)
    ds.SetProjection(projection.ExportToWkt())
    ds.GetRasterBand(1).WriteArray(data)
    del ds


### Entzippen

# ## Get zip files from the directory
# filelist = glob.glob(os.path.join(data_folder, "*.zip"))

# ## Unzip the files
# for zip_file in filelist:
#     with zipfile.ZipFile(zip_file, 'r') as zip_ref:
#         zip_ref.extractall(data_folder)
        
# # Find the unzipped folders
#         unzipped_folders = [os.path.join(data_folder, name) for name in os.listdir(data_folder) if os.path.isdir(os.path.join(data_folder, name))]

        
# ## AOI laden
# # Open crop extent (your study area extent boundary)
# crop_extent = gpd.read_file(aoi_path)

# # Check the CRS for AOI file
# crop_extent.crs

### Geotif öffnen

## Prepare input data for the loop and using above functions
scenes_df = df_from_dir(data_folder)
grouped = scenes_df.groupby(["sensdate"])
days = scenes_df["sensdate"].unique()
# get bounds from shapefile
# bounds_aoi = getBounds_Shp(aoi_path)
# get bounds from ASCII grid
bounds_aoi = get_bounds_from_mask(mask_file_path)
df_datestamp = pd.DataFrame(index=pd.Index(days, name='Date'))
df_datestamp["wetsnow_mean"] = np.nan
df_datestamp["wetsnow_sum"] = np.nan

# iterate through days
for day in days:
    group = grouped.get_group((day,))
    mean_datetime = str(group.sensdatetime.mean())
    print("processing {} with {} scenes".format(str(day)[0:10], group.shape[0]))

    outfile = "{}{}SWS_{}_{}.tif".format(
        output_folder,
        os.path.sep,
        mean_datetime[0:10].replace("-", "_"),
        mean_datetime[11:16].replace(":", "_"),
    )

    if os.path.isfile(outfile):
        print(
            "File {} already exists, skipping processing!".format(
                os.path.basename(outfile)
            )
        )

    else:
        ## extract wanted files from Zipfolders
        for i, scene_name in enumerate(group["filename"]):

            ## get FSCOG file from Archive
            zipfilepath = "{}{}{}.zip".format(data_folder, os.path.sep, scene_name)
            fileoutpath = "{}{}{}.tif".format(local_temp, os.path.sep, scene_name)

            try:
                z = zipfile.ZipFile(zipfilepath)
                with zipfile.ZipFile(zipfilepath) as z:
                    with open(fileoutpath, "wb") as f:
                        f.write(
                            z.read("{}/{}_WSM.tif".format(scene_name, scene_name))
                        )
                        f.close()
                    z.close()
            except Exception as e:
                writeLog(
                    log_path,
                    "Couldnt unzip file {} for folowing reason: {}".format(
                        e, zipfilepath
                    ),
                )

    scenes = glob.glob("{}{}SWS*.tif".format(local_temp, os.path.sep))

    # ## define geotrans tupel for hopi related Sentinel-2 tiles
    # hopi_geotrans = (499980, 20, 0, 5300040, 0, -20)
    # hopi_array = np.full(shape=(10491, 15489), fill_value=255)

    ## iterate through scenes
    for scene in scenes:

        ## readraster
        rasterarray, scene_geotrans, projection, bounds = readRaster(scene)
        rasterarray = rasterarray
        
        # get some infos from topo geotrans
        scene_min_x = scene_geotrans[0]
        scene_min_y = scene_geotrans[3]
        scene_res = scene_geotrans[1]
        # create topo_params list for clipping
        scene_params = [scene_min_x, scene_min_y, scene_res]

        # clip raster 
        data_aoi, geotrans_aoi = clipArray(rasterarray, scene_params, bounds_aoi)

        # Extract the date from the filename
        scene_filename = os.path.basename(scene)
        date_str = scene_filename.split("_")[1]
        current_date = dt.strptime(date_str, "%Y%m%dT%H%M%S")

        # Check if data_aoi has any values other than 255
        if np.all(data_aoi == 255):
            print(f"Skipping and removing scene {scene} as it contains only NaN values.")
            # Remove the corresponding date from the DataFrame
            # Check if the date exists in the DataFrame before attempting to drop it
            if current_date in df_datestamp.index:
                df_datestamp = df_datestamp.drop(current_date)
            else:
                print(f"{current_date} not found in DataFrame index, skipping drop.")
            continue
        


        ##replace nan value
        # rasterarray[rasterarray == 205] = 255 # welche Nodata Value haben die Daten
        # Saga GIS - kann NoData Value unten rechts im Fenster ausgegeben

    #     upperleftID = getPointID(hopi_geotrans, bounds[0], bounds[3])

    #     temp_array = np.full(shape=(10491, 15489), fill_value=255)

    #     temp_array[
    #         upperleftID[0] : upperleftID[0] + 5490,
    #         upperleftID[1] : upperleftID[1] + 5490,
    #     ] = rasterarray

    #     hopi_array[hopi_array == 255] = temp_array[hopi_array == 255]

    # ## set waterbodies from CORINE to nodata
    # hopi_array[corine_data == 512] = 255
    # hopi_array[corine_data == 511] = 255
        
        ## Set unwanted classes na and wet and dry snow to binary
        # wet snow
        data_aoi[data_aoi == 110] = 1
        # Dry snow or snow free or patchy snow
        data_aoi[data_aoi == 125] = 0
        # Radar shadow / layover / foreshortening
        data_aoi[data_aoi == 200] = 255
        # Water
        data_aoi[data_aoi == 210] = 255
        # Forest
        data_aoi[data_aoi == 220] = 255
        # Urban area
        data_aoi[data_aoi == 230] = 255
        # Non-mountain areas
        data_aoi[data_aoi == 240] = 255
        
        
        
        
        
        
        ## check combined Array for wetsnow information
        meanwetsnowarea = np.nanmean(data_aoi[data_aoi != 255])
        sumwetsnowpixels = np.nansum(data_aoi[data_aoi != 255]) 
    
        print("meanwetsnowpart of scene is: {}".format(meanwetsnowarea))
        print("wetsnowsum of scene is: {}".format(sumwetsnowpixels))
        
        if not np.isnan(meanwetsnowarea and sumwetsnowpixels):
            write_grid(outfile, data_aoi, geotrans_aoi, projection, dtype=gdal.GDT_Byte)
            
        ## write value in df_datestamp - it will contain the date and wetsnow information
        
        # match meanwetsnowarea with timestamp
        df_datestamp.loc[current_date, 'wetsnow_mean'] = meanwetsnowarea
        df_datestamp.loc[current_date, 'wetsnow_sum'] = sumwetsnowpixels 


    # if meansnowcover > snowcoverthreshold:
    #     outfile = "{}{}FSC_HOPI_{}_{}.tif".format(
    #         output_folder,
    #         os.path.sep,
    #         mean_datetime[0:10].replace("-", "_"),
    #         mean_datetime[11:16].replace(":", "_"),
    #     )
    #     write_grid(outfile, hopi_array, hopi_geotrans, projection, dtype=gdal.GDT_Byte)
    # else:
    #     print("snowcover in this scene too low, scene will not be written")

    ## Remove everything in tempfolder
    files = glob.glob("{}{}*".format(local_temp, os.path.sep))
    import time

    time.sleep(5)
    for f in files:
        os.remove(f)



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
