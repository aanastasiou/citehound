#!/bin/bash

# Athanasios Anastasiou Mar 2023
# Fetches the latest release of the GRID / ROR dataset
# For more information please see: https://www.grid.ac/downloads

if [ ! -d "GRID/" ]; then
    mkdir GRID/
fi

if [ -f "GRID/grid.zip" ]; then
    echo "grid.zip already exists, erase that file to download a fresh copy"
else
    wget -O GRID/grid.zip https://ndownloader.figshare.com/files/30895309
fi
