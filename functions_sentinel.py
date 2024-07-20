# -*- coding: utf-8 -*-

'''
Created on Tuesday Jul 13 10:23:12 2024

This script lists alle the functions that have been written in the course of 
Analyzing Sentinel data from Mount Zugspitze Germany.
The general aim is to derive wet snow areas.

@author: luis
'''
import os, glob, sys, zipfile, math
from osgeo import gdal, gdalconst, osr, ogr
from datetime import datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


#### from former run_SWS_processing_temp.py ########################################

def debug_log(message, log_path):
    #%%
    """
    Logs a debug message to the console and a log file with a timestamp.
    
    Parameters:
    message (str): The message to log.
    
    Prints:
    The message to the console.
    
    Writes:
    The message to a log file with a timestamp.
    """
    print(message)  # Print the message to the console
    with open(log_path, "a") as log_file:  # Open the log file in append mode
        log_file.write(f"{dt.now()}: {message}\n")  # Write the message with a timestamp
#%%


def read_ascii_grid(filename):
    #%%
    """
    Reads an ASCII grid file and extracts the header information and data.

    Parameters:
    filename (str): The path to the ASCII grid file.

    Returns:
    tuple: A tuple containing the following elements:
        - ncols (int): Number of columns in the grid.
        - nrows (int): Number of rows in the grid.
        - xllcorner (float): X coordinate of the lower left corner.
        - yllcorner (float): Y coordinate of the lower left corner.
        - cellsize (float): Size of each cell.
        - nodata_value (float): Value used to represent no data.
        - data (ndarray): 2D array of grid data.
    """

    # Open the ASCII grid file for reading
    with open(filename, 'r') as file:
        # Read the first six lines to get the header information
        header = [file.readline() for _ in range(6)]

    # Extract header information
    ncols = int(header[0].split()[1])        # Number of columns
    nrows = int(header[1].split()[1])        # Number of rows
    xllcorner = float(header[2].split()[1])  # X coordinate of the lower left corner
    yllcorner = float(header[3].split()[1])  # Y coordinate of the lower left corner
    cellsize = float(header[4].split()[1])   # Cell size
    nodata_value = float(header[5].split()[1])  # No data value

    # Read the rest of the file to get the grid data, skipping the first six lines (header)
    data = np.loadtxt(filename, skiprows=6)

    # Return the header information and data as a tuple
    return ncols, nrows, xllcorner, yllcorner, cellsize, nodata_value, data
#%%

def get_bounds_from_mask(mask_file_path):
    #%%
    """
    Computes the bounding box coordinates from an ASCII grid mask file.

    Parameters:
    mask_file_path (str): The path to the ASCII grid mask file.

    Returns:
    list: A list containing the bounding box coordinates [xmin, xmax, ymin, ymax].
    """
    # Read the ASCII grid file to get its header information and data
    ncols, nrows, xllcorner, yllcorner, cellsize, nodata_value, data = read_ascii_grid(mask_file_path)
    
    # Calculate the minimum and maximum X coordinates
    xmin = xllcorner
    xmax = xllcorner + ncols * cellsize
    
    # Calculate the minimum and maximum Y coordinates
    ymin = yllcorner
    ymax = yllcorner + nrows * cellsize
    
    # Return the bounding box coordinates as a list
    return [xmin, xmax, ymin, ymax]
#%%

def df_from_dir(directory):
    #%%
    """
    Creates a DataFrame from ZIP files in a specified directory. The ZIP files
    are expected to be SWS product files with a specific naming convention.

    Parameters:
    directory (str): The path to the directory containing the ZIP files.

    Returns:
    DataFrame: A DataFrame containing the tile code, sensing datetime,
               and filename for each SWS product file.
    """
    # Create a list of all ZIP files in the specified directory
    filelist = glob.glob("{}{}*.zip".format(directory, os.path.sep))

    # Check if all ZIP files start with "SWS" indicating they are FSC products
    if not all([os.path.basename(file).startswith("SWS") for file in filelist]):
        print("Not all Zipfiles seem to be SWS products! Check Data Folder! \nAborting Script execution...")
        sys.exit()

    # Extract the base filenames without extensions
    filelist = [os.path.basename(file).split(".")[0] for file in glob.glob("{}{}*.zip".format(directory, os.path.sep))]

    # Extract sensing dates and times from the filenames and convert to datetime objects
    sens_dates = [dt.strptime(file.split("_")[1], "%Y%m%dT%H%M%S") for file in filelist]
    
    # Sort the sensing dates
    sens_dates.sort()

    # Extract tile codes from the filenames
    tiles = [file.split("_")[3] for file in filelist]

    # Create a DataFrame with the extracted information
    scenes_df = pd.DataFrame({"tilecode": tiles, "sensdatetime": sens_dates, "filename": filelist})
    
    # Round the sensing datetime to the nearest hour and add as a new column
    scenes_df["sensdate"] = scenes_df["sensdatetime"].round("h")

    return scenes_df
#%%

def writeLog(logfilepath, string, verbose=True):
    #%%
    """
    Writes a log entry to a specified log file, with an option to print the log entry.

    Parameters:
    logfilepath (str): The path to the log file.
    string (str): The message to be logged.
    verbose (bool): If True, prints the log entry to the console. Default is True.
    """
    # Get the current date and time as a string (up to seconds)
    timestring = str(dt.now())[0:19]

    # Check if the log file already exists
    if os.path.isfile(logfilepath):
        # If the file exists, open it in append mode and write the log entry
        with open(logfilepath, "a") as writefile:
            writefile.write("\n{}: {}".format(timestring, string))
    else:
        # If the file does not exist, create it and write the log entry
        with open(logfilepath, "w") as writefile:
            writefile.write("\n{}: {}".format(timestring, string))

    # If verbose is True, print the log entry to the console
    if verbose:
        print(string)
#%%

def clipArray(src_data, params, bound, log_path, offsetx=0, offsety=0):
    #%%
    """
    Clips a portion of a 2D array (representing raster data) based on the specified bounds.

    Parameters:
    src_data (ndarray): The source 2D array containing raster data.
    params (tuple): A tuple containing the following elements:
        - srcMinX (float): The minimum X coordinate of the source data.
        - srcMaxY (float): The maximum Y coordinate of the source data.
        - res (float): The resolution of the data (cell size).
    bound (tuple): A tuple containing the clipping bounds:
        - minX (float): The minimum X coordinate of the clipping area.
        - maxX (float): The maximum X coordinate of the clipping area.
        - minY (float): The minimum Y coordinate of the clipping area.
        - maxY (float): The maximum Y coordinate of the clipping area.
    offsetx (int, optional): The offset in the X direction. Default is 0.
    offsety (int, optional): The offset in the Y direction. Default is 0.

    Returns:
    tuple: A tuple containing:
        - clip (ndarray): The clipped portion of the source data.
        - geoTrans (list): The geotransform of the clipped data.
    """
    # Extract resolution and source bounds from parameters
    res = params[2]
    srcMinX = params[0]
    srcMaxY = params[1]

    # Extract clipping bounds
    minX = bound[0]
    maxX = bound[1]
    minY = bound[2]
    maxY = bound[3]

    # Calculate row and column indices for clipping
    rowMin = int(math.ceil((srcMaxY - minY) / res))
    rowMax = int(round((srcMaxY - maxY) / res))
    colMin = int(round((minX - srcMinX) / res))
    colMax = int(math.ceil((maxX - srcMinX) / res))

    # Clip the array using calculated indices and offsets
    clip = src_data[rowMax + offsety:rowMin + offsety, colMin + offsetx:colMax + offsetx]

    # Calculate new geotransform for the clipped array
    minXclip = srcMinX + colMin * res
    maxYclip = srcMaxY - rowMax * res
    geoTrans = [minXclip, res, 0, maxYclip, 0, -res]

    # Log debug information
    debug_log(f"Clipping array with bounds: {bound}", log_path)
    debug_log(f"Clipped data shape: {clip.shape}", log_path)

    return clip, geoTrans
#%%

def getBounds_Shp(shapefile):
    #%%
    """
    Retrieves the bounding box coordinates from a shapefile.

    Parameters:
    shapefile (str): The path to the shapefile.

    Returns:
    tuple: A tuple containing the bounding box coordinates (xmin, xmax, ymin, ymax).
    """
    # Open the shapefile in read-only mode (0)
    shapeData = ogr.Open(shapefile, 0)
    
    # Check if the shapefile was successfully opened
    if not shapeData:
        raise FileNotFoundError(f"Unable to open the shapefile: {shapefile}")
    
    # Get the layer from the shapefile
    layer = shapeData.GetLayer()
    
    # Get the extent of the layer, which returns the bounding box coordinates
    bounds = layer.GetExtent()
    
    # Return the bounding box coordinates as a tuple (xmin, xmax, ymin, ymax)
    return bounds
#%%

def getBounds_Raster(ds):
    #%%
    """
    Retrieves the bounding box coordinates from a raster dataset.

    Parameters:
    ds (gdal.Dataset): The raster dataset object.

    Returns:
    list: A list containing the bounding box coordinates [minX, maxX, minY, maxY].
    """
    # Get the geotransformation information from the dataset
    geoTrans = ds.GetGeoTransform()
    
    # Get the width and height of the raster
    width = ds.RasterXSize
    height = ds.RasterYSize
    
    # Extract the resolution (pixel size) from the geotransformation
    res = geoTrans[1]
    
    # Calculate the minimum and maximum X coordinates
    minX = geoTrans[0]
    maxX = minX + width * res
    
    # Calculate the minimum and maximum Y coordinates
    maxY = geoTrans[3]
    minY = maxY - height * res
    
    # Store the bounding box coordinates in a list
    bounds = [minX, maxX, minY, maxY]
    
    # Return the bounding box coordinates
    return bounds
#%%

def readRaster(filename):
    #%%
    """
    Reads a raster file and retrieves its data, projection, geotransformation, and bounding box.

    Parameters:
    filename (str): The path to the raster file.

    Returns:
    tuple: A tuple containing:
        - data (ndarray): The raster data as a 2D array.
        - projection (osr.SpatialReference): The spatial reference system of the raster.
        - geotrans (tuple): The geotransformation parameters of the raster.
        - bounds (list): The bounding box coordinates [minX, maxX, minY, maxY].
    """
    # Open the raster file
    ds = gdal.Open(filename)
    
    if ds is None:
        raise FileNotFoundError(f"Unable to open the raster file: {filename}")
    
    # Read the first raster band (assuming the raster is single-band)
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray()

    # Retrieve the spatial reference system (projection)
    projection = osr.SpatialReference()
    projection.ImportFromWkt(ds.GetProjectionRef())

    # Retrieve the geotransformation parameters
    geotrans = ds.GetGeoTransform()

    # Calculate the bounding box coordinates
    bounds = getBounds_Raster(ds)
    
    # Return the raster data, projection, geotransformation, and bounding box
    return data, geotrans, projection, bounds
#%%

def getClipParams(ds):
    #%%
    """
    Retrieves clipping parameters from a raster dataset.

    Parameters:
    ds (gdal.Dataset): The raster dataset object.

    Returns:
    list: A list containing the source minimum X coordinate, source maximum Y coordinate, and resolution.
    """
    # Get the geotransformation information from the dataset
    geoTrans_src = ds.GetGeoTransform()

    # Extract the resolution (pixel size) from the geotransformation
    res = geoTrans_src[1]

    # Extract the minimum X coordinate from the geotransformation
    srcMinX = geoTrans_src[0]

    # Extract the maximum Y coordinate from the geotransformation
    srcMaxY = geoTrans_src[3]

    # Create a list of the extracted parameters
    params = [srcMinX, srcMaxY, res]

    # Return the list of clipping parameters
    return params
#%%

def write_grid(filename, data, geotrans, projection, log_path, driver="GTiff", dtype=None):
    #%%
    """
    Writes a raster grid to a file.

    Parameters:
    filename (str): The path to the output raster file.
    data (ndarray): The 2D array containing the raster data.
    geotrans (tuple): The geotransformation parameters.
    projection (osr.SpatialReference): The spatial reference system of the raster.
    driver (str, optional): The GDAL driver to use for writing the file. Default is "GTiff".
    dtype (optional): The data type for the output raster. Default is gdalconst.GDT_Float32.

    Raises:
    ValueError: If the specified driver is not available or if dataset creation fails.
    """
    # Log the process of writing the grid
    debug_log(f"Writing grid to file: {filename}", log_path)
    debug_log(f"Data shape: {data.shape}, Geotransform: {geotrans}, Projection: {projection.ExportToWkt()}", log_path)

    # Set the default data type if not provided
    if dtype is None:
        dtype = gdalconst.GDT_Float32

    # Get the GDAL driver by name
    driver = gdal.GetDriverByName(driver)
    if driver is None:
        debug_log("Driver GTiff is not available.", log_path)
        raise ValueError("Driver GTiff is not available.")

    # Log the creation of the file with specified dimensions
    debug_log(f"Creating file with dimensions: {data.shape[1]}, {data.shape[0]}", log_path)

    # Create the output dataset with the specified dimensions, data type, and compression
    ds = driver.Create(filename, data.shape[1], data.shape[0], 1, dtype, ["COMPRESS=LZW"])
    if ds is None:
        debug_log("Failed to create the dataset.", log_path)
        raise ValueError("Failed to create the dataset.")

    # Set the geotransformation parameters and projection for the dataset
    ds.SetGeoTransform(geotrans)
    ds.SetProjection(projection.ExportToWkt())

    # Write the raster data to the dataset
    ds.GetRasterBand(1).WriteArray(data)

    # Log the completion of the writing process
    debug_log("Finished writing the grid.", log_path)

    # Properly close and flush the dataset
    del ds
#%%

def create_unique_filename(output_folder, base_name, ext):
    #%%
    """
    Creates a unique filename in the specified output folder by appending a counter to the base name if a file with the same name already exists.

    Parameters:
    output_folder (str): The path to the folder where the file will be saved.
    base_name (str): The base name for the file (without extension).
    ext (str): The file extension (without leading dot).

    Returns:
    str: A unique filename with the specified base name and extension in the output folder.
    """
    # Initialize the counter for creating unique filenames
    counter = 1
    
    # Start with the initial filename
    unique_name = f"{base_name}.{ext}"
    
    # Check if a file with the current unique_name exists in the output folder
    while os.path.exists(os.path.join(output_folder, unique_name)):
        # If it exists, create a new filename by appending the counter to the base name
        unique_name = f"{base_name}_{counter}.{ext}"
        # Increment the counter for the next iteration
        counter += 1
    
    # Return the full path of the unique filename
    return os.path.join(output_folder, unique_name)
#%%

def clear_temp_directory(temp_directory):
    #%%
    """
    Clears the specified temporary directory by removing all files within it.

    Parameters:
    temp_directory (str): The path to the temporary directory to be cleared.
    """
    # Create a list of all files in the temporary directory
    files = glob.glob(os.path.join(temp_directory, "*"))
    for f in files:
        try:
            os.remove(f)
            print(f"Removed file: {f}")
        except Exception as e:
            print(f"Failed to remove {f}: {e}")
#%%


#### from run_plot_analysis.py ################################################

def process_and_plot_tif_binary(file_path, output_directory):
    #%%
    # Load the TIF file using GDAL
    dataset = gdal.Open(file_path)
    band = dataset.GetRasterBand(1)
    data = band.ReadAsArray()

    # Convert the array to float type
    data = data.astype(float)

    # Mask the non-classified values (255) by setting them to NaN
    data[data == 255] = np.nan

    # Define the colors for the plot
    cmap = plt.matplotlib.colors.ListedColormap(['grey', 'blue'])
    bounds = [0, 1, 2]
    norm = plt.matplotlib.colors.BoundaryNorm(bounds, cmap.N)

    # Plot the data
    plt.figure(figsize=(10, 10))
    plt.imshow(data, cmap=cmap, norm=norm, interpolation='none')
    cbar = plt.colorbar(ticks=[0, 1])
    cbar.ax.set_yticklabels(['Dry Snow, No Snow \n or Patchy Snow (0)', 'Wet Snow (1)'])
    cbar.set_label('Snow Type')

    # Extract the date from the file name (assuming format SWS_20240521T052708_S1A_T32TPT_V101_1_WSM.tif)
    base_name = os.path.basename(file_path)
    parts = base_name.split('_')

    # Split the last part by '.' to remove the extension
    parts[-1] = parts[-1].split('.')[0]


    # Format the date string with hours and minutes
    date_str = f"{parts[1]}_{parts[2]}_{parts[3]}_{parts[4]}h_{parts[5]}m"
    
    # Save the plot
    output_file_path = os.path.join(output_directory, f"{date_str}_SWS_map.png")
    plt.title(f'Snow Classification Map for {date_str}')
    plt.savefig(output_file_path)
    plt.close()

    # Print completion message
    print(f"Finished processing {base_name} and saved to {output_file_path}")
#%%

def process_and_plot_tif_all_classes(file_path, output_directory):
    #%%
    # Load the TIF file using GDAL
    dataset = gdal.Open(file_path)
    band = dataset.GetRasterBand(1)
    data = band.ReadAsArray()

    # Replace specific values in the data
    data[data == 110] = 1
    data[data == 125] = 0
    data[data == 200] = 21
    data[data == 210] = 22
    data[data == 220] = 23
    data[data == 230] = 24
    data[data == 240] = 25

    # Convert the array to float type
    data = data.astype(float)

    # Mask the non-classified values (255) by setting them to NaN
    data[data == 255] = np.nan

    # Define the colors for the plot
    cmap = plt.matplotlib.colors.ListedColormap([
        'grey', 'blue', 'black', 'cyan', 'green', 'red', 'yellow'
    ])
    bounds = [0, 1, 21, 22, 23, 24, 25, 256]
    norm = plt.matplotlib.colors.BoundaryNorm(bounds, cmap.N)

    # Plot the data
    plt.figure(figsize=(10, 10))
    img = plt.imshow(data, cmap=cmap, norm=norm, interpolation='none')
    cbar = plt.colorbar(img, ticks=[0, 1, 21, 22, 23, 24, 25])
    cbar.ax.set_yticklabels([
        'Dry Snow (0)', 'Wet Snow (1)', 'Radar shadow / layover / foreshortening (21)',
        'Water (22)', 'Forest (23)', 'Urban area (24)', 'Non-mountain areas (25)'
    ])
    cbar.set_label('Classification')

    # Extract the date from the file name (assuming format SWS_20240521T052708_S1A_T32TPT_V101_1_WSM.tif)
    base_name = os.path.basename(file_path)
    print(f"This is the filepath: {file_path}")
    # Split the base name by underscores
    parts = base_name.split('_')
    
    # Debugging prints to understand the filename structure
    print(f"Filename parts: {parts}")
    
    if len(parts) < 3:
        print(f"Unexpected filename format: {base_name}")
        return

    
    # Extract the date from the file name (assuming format SWS_20240521T052708_S1A_T32TPT_V101_1_WSM.tif)
    base_name = os.path.basename(file_path)
    parts = base_name.split('_')

    # Split the last part by '.' to remove the extension
    parts[-1] = parts[-1].split('.')[0]


    # Format the date string with hours and minutes
    date_str = f"{parts[1]}_{parts[2]}_{parts[3]}_{parts[4]}h_{parts[5]}m"
    
    # Save the plot
    output_file_path = os.path.join(output_directory, f"{date_str}_classification_map.png")
    plt.savefig(output_file_path)
    plt.close()

    # Print completion message
    print(f"Finished processing {base_name} and saved to {output_file_path}")
#%%



def process_directory(input_directory, output_directory, use_binary=False):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for filename in os.listdir(input_directory):
        if filename.endswith('.tif'):
            file_path = os.path.join(input_directory, filename)
            if use_binary:
                
                process_and_plot_tif_binary(file_path, output_directory)
            else:
                process_and_plot_tif_all_classes(file_path, output_directory)
#%%