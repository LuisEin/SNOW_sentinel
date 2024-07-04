# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 14:35:30 2024

@author: pschattan
"""

try:
    from osgeo import ogr, gdal, osr
except:
    import ogr, gdal, osr
import math


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
    # TODO: replace round by math.floor. Check INCA_DEM before (coords shifted by 500m)
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

# get bounds of AOI (in the same coordinate system as your planet scene)
# Ecken definieren, in koordinatensystem der "großen" Daten. recht wahrscheinlich: epsg = 32632
# Im GIS umprojizieren

# variant 1: define bounds manually
bounds_aoi = [min_x, max_x, min_y, max_y]

# variant 2: define using shapefile (check projection!)
bounds_aoi = getBounds_Shp(path_to_shapefile)

# variant 3: define using raster (check projection!)
bounds_aoi = getBounds_Shp(path_to_raster)

scene = "filename_of_geotiff"
rasterarray, scene_geotrans, projection, bounds = readRaster(scene)

# get some infos from topo geotrans
scene_min_x = scene_geotrans[0]
scene_min_y = scene_geotrans[3]
scene_res = scene_geotrans[1]
# create topo_params list for clipping
scene_params = [scene_min_x, scene_min_y, scene_res]

# clip raster 
data_aoi, geotrans_aoi = clipArray(rasterarray, scene_params, bounds_aoi)