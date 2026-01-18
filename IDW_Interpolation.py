##Python Challenge 8a
#Create a Python script for interpolating a meaningful raster from a point cloud dataset
#Using IDW(inverse distance weighting) interpolation method)


# region 1. Environment Setup #

import os                           ## for file path manipulations
import sys                          ## for system specific parameters and functions    

import numpy as np                  ## for numerical operations

from osgeo import gdal              ## for raster data processing
from osgeo import ogr               ## for vector data processing

# endregion #

# region 2. File Directory Configurations #

#==Define file paths==
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DATA = os.path.join(BASE_DIR, "input_data")
OUTPUT_DATA = os.path.join(BASE_DIR, "output_data")

# endregion #

# region 3. Core Function Definitions #
def defence_check():
    """
    Function to perform initial checks and setup.
    Ensures input/output directories exist and are accessible.
    """
    #==Check if in- and output data directory exists==
    if not os.path.exists(INPUT_DATA):
        os.makedirs(INPUT_DATA)
        print(
            f"You don't have an Input data directory. Input data directory is created at: {INPUT_DATA}.\n"
            f"Please add required input data files and re-run the script."
            )
        return False 
    elif not os.path.exists(OUTPUT_DATA):
        os.makedirs(OUTPUT_DATA)
        print(
            f"You don't have an Output data directory. Output data directory is created at: {OUTPUT_DATA}.\n"
            f"Please add required output data files and re-run the script."
            )
        return False
    #==Check if .shp file exists==
    ###############################################################################
    ### i didn't setup file checking for other file types like .shx, .dbf, etc. ###
    ###############################################################################
    input_shp_files = []
    for file in os.listdir(INPUT_DATA):
        if file.endswith(".shp"):
            input_shp_files.append(file)

    if len(input_shp_files) == 0:
        print(
            f"No shapefile(.shp) found in Input data directory: {INPUT_DATA}.\n"
            f"Please add required input data files and re-run the script."
            )
        return False
    return True

def shp_reader(shp_path, z_field="Z"):
    """
    Function to read a shapefile and extract point data.
    
    Parameters:
    shp_path (str): Path to the input shapefile. Gotten from INPUT_DATA directory.
    z_field (str): Name of the field containing Z values. Gotten from the attribute table of the shapefile.
    
    Returns:
    points (list): List of tuples containing (X, Y, Z) coordinates.
    spatial_ref (osr.SpatialReference): Spatial reference of the shapefile.

    """
    #==1.Open shapefile==
    datasource = ogr.Open(shp_path)

    if datasource is None:  ###defence check for data source
        print(f"Could not open {shp_path}.")
        return None, None
    
    #==2.Get layer and spatial reference==
    layer = datasource.GetLayer()
    spatial_ref = layer.GetSpatialRef()

    #==3.Extract point data==
    all_points = []

    for p_feature in layer:
        #==Get geometry and coordinates==
        geom = p_feature.GetGeometryRef()

        #==Get X, Y, Z values==
        x = geom.GetX()
        y = geom.GetY()
        z = p_feature.GetField(z_field)

        #==Append the point to the list==
        if z is not None:
            all_points.append((x, y, z))
    
    #==4.Convert to numpy array==
    all_points = np.array(all_points)

    #==5.Issue feedback==
    print(f"System has successfully read {len(all_points)} points from {shp_path}.")

    #==6.Return points andspatial reference==
    datasource = None  ###close the data source
    return all_points, spatial_ref

def raster_region_setup(all_points, cell_size):
    """
    Function to set up raster region based on point data.
    
    Parameters:
    all_points (numpy.ndarray): Array of point coordinates and values. Gotten from shp_reader function.
    cell_size (float): Cell size for the output raster. 
    
    Returns:
    extents (tuple): Tuple containing (x_min, x_max, y_min, y_max).
    """
    #==1.Extract X and Y coordinates to calculate extents of raster region==
    all_x = all_points[:, 0]
    all_y = all_points[:, 1]

    #==2.Calculate min and max values to calculate extents of raster region==
    all_x_min = all_x.min()
    all_x_max = all_x.max()
    all_y_min = all_y.min()
    all_y_max = all_y.max()

    #==3.Calculate raster extents==
    cols = int((all_x_max - all_x_min) / cell_size) + 1
    rows = int((all_y_max - all_y_min) / cell_size) + 1

    #==4.Return extents as a tuple==
    extent = {
        'all_x_min': all_x_min,
        'all_x_max': all_x_max,
        'all_y_min': all_y_min,
        'all_y_max': all_y_max,
        'cols': cols,
        'rows': rows,
        'cell_size': cell_size
        }
    
    print(f"Raster region setup complete with extents: {extent}")
    print(f"Raster will have {cols} columns and {rows} rows with cell size {cell_size}.")

    return extent

def idw_interpolation(all_points,extent, power):
    """
    Function to perform IDW interpolation on point data.
    
    Parameters:
    all_points (numpy.ndarray): Array of point coordinates and values. Gotten from shp_reader function.
    extent (dict): Dictionary containing raster extents and cell size. Gotten from raster_region_setup function.
    power (int): Power parameter for IDW interpolation. Default is 2.
    
    Returns:
    raster (numpy.ndarray): 2D array representing the interpolated raster.
    """
    #==1.Extract raster parameters from extent data==
    x_min = extent['all_x_min']
    y_max = extent['all_y_max']
    cols = extent['cols']
    rows = extent['rows']
    cell_size = extent['cell_size']

    #==2.Build an empty raster array for storing interpolated values==
    initial_raster_data = np.zeros((rows, cols), dtype=np.float32)

    #==3.Extract all point coordinates and values for interpolation==
    interpo_x = all_points[:, 0]
    interpo_y = all_points[:, 1]
    interpo_z = all_points[:, 2]

    #==4.Perform IDW interpolation==
    for r in range(rows):
        for c in range(cols):
            
            ##==4.1 Calculate the center coordinates of the current raster cell==##
            target_x = x_min + c * cell_size + cell_size / 2
            target_y = y_max - r * cell_size - cell_size / 2

            ##==4.2 Calculate distances from all points to the target cell center==##
            ## d = sqrt((x2-x1)² + (y2-y1)²) ##
            distances = np.sqrt((interpo_x - target_x) ** 2 + (interpo_y - target_y) ** 2)

            ##==4.3 Avoid division by zero by setting a minimum distance threshold==##
            distances[distances < 1e-10] = 1e-10

            ##==4.4 Calculate weights based on distances and power parameter==##
            weights = 1 / (distances ** power)

            ##==4.5 Calculate the interpolated value for the target cell==##
            ## z = Σ(w × z) / Σ(w) ##
            upper_p = np.sum(weights * interpo_z)
            lower_p = np.sum(weights)
            interpolated_value = upper_p / lower_p

            initial_raster_data[r, c] = interpolated_value  

        if (r + 1) % 10 == 0 or r == rows - 1:
            progress = (r + 1) / rows * 100
            print(f"Progress: {r + 1}/{rows} Row ({progress:.1f}%)")
            
    print("IDW interpolation complete.")
    return initial_raster_data

def raster_saver(raster_data, extent, spatial_ref, output_path):
    """
    Function to save raster data to a GeoTIFF file.
    
    Parameters:
    raster_data (numpy.ndarray): gotten from idw_interpolation function.
    extent (dict): Dictionary containing raster extents and cell size. Gotten from raster_region_setup function.
    spatial_ref (osr.SpatialReference): Spatial reference of the raster. Gotten from shp_reader function.
    output_path (str): Path to save the output GeoTIFF file.
    """
    ##==1. Earn extents and cell size from extent data==##
    x_min = extent['all_x_min']
    y_max = extent['all_y_max']
    cols = extent['cols']
    rows = extent['rows']
    cell_size = extent['cell_size'] 

    ##==2. Set up GeoTIFF driver to create a new raster file==##
    driver = gdal.GetDriverByName("GTiff")

    ##==3. Create a new raster dataset==##
    ##==Parameters: output path, number of columns, number of rows, number of bands, data type==##
    out_raster = driver.Create(
        output_path,
        cols,
        rows,
        1,
        gdal.GDT_Float32
        )
    
    ##==4. Define geotransform and projection parameters for the raster==##
    geotransform = (
        x_min,
        cell_size,
        0,
        y_max,
        0,
        -cell_size
        )
    out_raster.SetGeoTransform(geotransform)

    ##==5. Set spatial reference for the raster==##
    if spatial_ref is not None:
        out_raster.SetProjection(spatial_ref.ExportToWkt())

    ##==6. Write raster data to the raster band==##
    out_band = out_raster.GetRasterBand(1)
    out_band.WriteArray(raster_data)
    out_band.SetNoDataValue(-9999)

    #==7. Close the raster dataset==
    out_raster = None
    print(f"Raster saved successfully at: {output_path}")

def main():
    """
    Main function to execute the IDW interpolation workflow.
    """
    ##==1.Parameter setup==##
    input_shp_file = os.path.join(INPUT_DATA, "U2d-Q330.shp")
    output_raster_file = os.path.join(OUTPUT_DATA, "idw_interpolated_raster.tif")
    z_field_name = "depth_aver"  ##name of the field containing Z values in the shapefile
    cell_size = 2      ##cell size for the output raster
    power = 2           ##power parameter for IDW interpolation

    ##==2.Check output and input directories==##
    if not defence_check():
        sys.exit()

    ##==3.Light Interface==##
    print("="*50)
    print(" Python Challenge 8a: IDW Interpolation Tool ")
    print("="*50)

    ##==4.Read point data from shapefile==##
    print("\nReading point data from shapefile...")
    all_points, spatial_ref = shp_reader(input_shp_file, z_field=z_field_name)
    if all_points is None:
        sys.exit()
    
    ##==5.Setup raster region based on point data==##
    print("\nSetting up raster region...")
    extent = raster_region_setup(all_points, cell_size=cell_size)

    ##==6.Perform IDW interpolation==##
    print("\nPerforming IDW interpolation...")
    raster_data = idw_interpolation(all_points, extent, power=power)

    ##==7.Save interpolated raster to GeoTIFF file==##
    print("\nSaving interpolated raster to GeoTIFF file...")
    raster_saver(raster_data, extent, spatial_ref, output_raster_file)

    print("="*50)
    print(" IDW Interpolation Process Completed Successfully ")
    print("="*50)

if __name__ == "__main__":
    main()