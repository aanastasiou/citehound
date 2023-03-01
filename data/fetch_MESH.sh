#!/bin/bash

# Athanasios Anastasiou Mar 2023
#
# Downloads all available MeSH XML files from Medline and creates an "index"
# file that is used in creating a summary file from all of these XML 
# files. This file summarises all of the transactions in the MESH data
# over the described timespan.
#

banner () {
    echo -e "Citehound -- fetchMESH\nDownloading MESH historical data\n\n"
}



banner
# Decide which file is to be processed
if [ $# -eq 0 ]; then
    echo -e "WARNING: Using default:mesh_xml_historical_data.txt\n"
    file_to_process="mesh_xml_historical_data.txt"
else
    file_to_process=$1
fi

# Check that the file exists
if [ ! -f $file_to_process ]; then
    echo -e "!!!ERROR!!!:File $file_to_process does not exist\n"
    exit 1
fi

# Create the MESH directory if required
if [ ! -d "MESH/" ]; then
    mkdir MESH
fi

# Now download all of the data (this might take some time)
echo -e "Downloading data. This might take some time (and disk space)\n"

while read a_file;do
    # Get the base name of the file
    a_file_basename=`basename ${a_file}`
    # If it has not been downloaded yet, download it
    if [ ! -f "MESH/${a_file_basename}" ]; then
        wget -O MESH/${a_file_basename} https://nlmpubs.nlm.nih.gov/projects/mesh/${a_file}
    fi
done < ${file_to_process}
