# -*- coding: utf-8 -*-
"""
Created on Mon Dec 14 16:06:01 2020

@author: ms
"""
import os, glob, sys, zipfile, math
from osgeo import gdal, gdalconst, osr
from datetime import datetime as dt
import numpy as np
import pandas as pd

# data_folder = 'B:/Projekte_alt/h01h02/2019_HoPI4_Teil2_Neuableitung/Bearbeitung/AP4 - Kalibrierung der Teileinzugsgebiete/Fernerkundungsdaten/Copernicus_HighRes_FSC/downloader/Data'
data_folder = ".\\Data"
local_temp = ".\\temp"
output_folder = ".\\results"
corinepath = ".\\resources\\FSC_CORINE_Raster4.tif"
log_path = ".\\logfile.txt"

snowcoverthreshold = 1.5


def df_from_dir(directory):
    # get zip files from directory and read tilecode and timestamp from
    filelist = glob.glob("{}{}*.zip".format(directory, os.path.sep))

    if not all([os.path.basename(file).startswith("FSC") for file in filelist]):
        print(
            "Not all Zipfiles seem to be FSC products! Check Data Folder! \nAborting Script execution..."
        )
        sys.exit()

    filelist = [
        os.path.basename(file).split(".")[0]
        for file in glob.glob("{}{}*.zip".format(directory, os.path.sep))
    ]

    sens_dates = [dt.strptime(file.split("_")[1], "%Y%m%dT%H%M%S") for file in filelist]
    tiles = [file.split("_")[3] for file in filelist]

    # build DF
    scenes_df = pd.DataFrame(
        {"tilecode": tiles, "sensdatetime": sens_dates, "filename": filelist}
    )

    scenes_df["sensdate"] = scenes_df["sensdatetime"].round("h")

    return scenes_df


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


# def getPointID(geoTrans, xcoord, ycoord):
#     """returns rows and colums of a point. """
#     res = geoTrans[1]
#     basinMinX = geoTrans[0]
#     basinMaxY = geoTrans[3]
#     row = int(math.floor((basinMaxY - ycoord) / res))
#     col = int(math.floor((xcoord - basinMinX) / res))
#     return row, col


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


scenes_df = df_from_dir(data_folder)
grouped = scenes_df.groupby(["sensdate"])
days = scenes_df["sensdate"].unique()

# # read Corine data once
# corine_data, corine_geotrans, corine_projection, corine_bounds = readRaster(corinepath)

# iterate through days
for day in days:
    group = grouped.get_group(day)
    mean_datetime = str(group.sensdatetime.mean())
    print("processing {} with {} scenes".format(str(day)[0:10], group.shape[0]))

    outfile = "{}{}FSC_HOPI_{}_{}.tif".format(
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
                            z.read("{}/{}_FSCOG.tif".format(scene_name, scene_name))
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

    ## define geotrans tupel for hopi related Sentinel-2 tiles
    hopi_geotrans = (499980, 20, 0, 5300040, 0, -20)
    hopi_array = np.full(shape=(10491, 15489), fill_value=255)

    ## iterate through scenes
    for scene in scenes:

        ## readraster
        rasterarray, scene_geotrans, projection, bounds = readRaster(scene)
        rasterarray = rasterarray
        
        # Hier clippen wie im clipScript

        ##replace nan value
        rasterarray[rasterarray == 205] = 255 # welche Nodata Value haben die Daten
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

    ## check combined Array for snowcover
    meansnowcover = hopi_array[hopi_array != 255].mean() # Auf geclippten Datenarray beziehen

    print("meansnowcover of scene is: {}".format(meansnowcover))

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

# datelist = [date_obj1, date_obj2]

# df = pd.DataFrame(index=datelist)
# df["wetsnow_area"] = np.nan
# df.loc[(datetime, "wetsnow_area")] = einzelwert