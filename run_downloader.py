import os
import glob
import shutil

start_date = "2018-01-01"
end_date = "2024-07-16"
data_storage = "data"
local_temp_storage = "./temp"

credential_file = "./credentials.txt"
product_type = "FSC"

cloudcover = "10"

tile_list = ['32TPT']

for tile in tile_list:
    print("Searching for tile {}".format(tile))
    callstring = (
        "python ./CLMS_downloader.py {} -query -productType {} -productIdentifier {} "
        "-obsDateMin {}T00:00:00Z -obsDateMax {}T00:00:00Z -cloudCoverageMax {}".format(
            local_temp_storage, product_type, tile, start_date, end_date, cloudcover
        )
    )
    os.system(callstring)

    ## compare files from query with files that already exist in directory
    with open("{}/result_file.txt".format(local_temp_storage), "r") as resultfile:
        lines = resultfile.readlines()

    querylist = [line.split(";")[-1].strip() for line in lines]

    existlist = [
        os.path.basename(file).split(".")[0]
        for file in glob.glob("{}/*{}*.zip".format(data_storage, tile))
    ]

    files_to_load = [line for line in lines if line.split(";")[-1].strip() not in existlist]

    print(
        "Found {} existing files and {} new files to load!".format(
            len(existlist), len(files_to_load)
        )
    )
    if files_to_load:
        with open("{}/result_file.txt".format(local_temp_storage), "w") as resultfile:
            resultfile.write("".join(files_to_load))

        ## Hier wird das auszuführende Skript gecalled!! ##
        callstring = (
            "python ./clms_hrsi_downloader_new.py {} -hrsi_credentials {} -download "
            "-result_file {}/result_file.txt".format(local_temp_storage, credential_file, local_temp_storage)
        )
        os.system(callstring)

for file in glob.glob("{}/*.zip".format(local_temp_storage)):
    print(file, os.path.basename(file))
    shutil.move(file, "{}/{}".format(data_storage, os.path.basename(file)))
