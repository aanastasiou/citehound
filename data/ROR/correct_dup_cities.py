#!/usr/bin/env python
"""
A brief script to indicate the "location" of a possibly mispelled 'Washington' 
in the current (v1.20-2023-02-28-ror-data.json) ROR dataset


:author: Athanasios Anastasiou
:date: Mar 2023
"""

import json
import click
import sys
import os
import collections
import pandas

@click.command()
@click.argument("data_in", type=click.Path(file_okay=True, dir_okay=False, exists=True, resolve_path=True, allow_dash=True))
@click.option("-c", "--corrections-file", type=click.Path(file_okay=True, dir_okay=False, exists=True, resolve_path=True))
def correct_dup_cities(data_in, corrections_file):
    """
    Finds and corrects divergent ("City") entries
    """
    # Load the data file
    if data_in == "-":
        data = json.load(sys.stdin)
    else:
        with open(data_in, "r") as fd:
            data = json.load(fd)

    if corrections_file is None:
        # Get all possible City names
        geo_id_name = {}
        for item_idx, an_item in enumerate(data):
            for address_item_idx, an_address_item in enumerate(an_item["addresses"]):
                if "geonames_city" in an_address_item and "id" in an_address_item["geonames_city"]:
                    city_id = an_address_item["geonames_city"]["id"]
                    city_name = an_address_item["geonames_city"]["city"]

                    if city_id not in geo_id_name:
                        geo_id_name[city_id] = {}
                        geo_id_name[city_id]["indexed_data"] = []

                    geo_id_name[city_id]["indexed_data"].append((city_name, item_idx, address_item_idx))

        # If a corrections file is not provided then generate the base for it along with the cached index data
        # Print uniques from each id
        for a_city_id, a_city_data in geo_id_name.items():
            entries = collections.Counter(map(lambda x:x[0], a_city_data["indexed_data"]))
            entry_items = entries.items()
            if len(entry_items)>1:
                geo_id_name[a_city_id]["cached_counts"] = entries
                click.echo(f"{a_city_id}, {','.join(map(lambda x:f'{x[0]}:{x[1]}',entry_items))}")
        
        with open(f"{os.path.splitext(data_in)[0]}_cities_cache.json", "w") as fd:
            json.dump(dict(filter(lambda x:"cached_counts" in x[1], geo_id_name.items())), fd)
    else:
        # Load the data file, cached index and corrections file and apply the corrections
        with open(f"{os.path.splitext(data_in)[0]}_cities_cache.json", "r") as fd:
            geo_id_name = json.load(fd)

        corrections = pandas.read_csv(corrections_file, header=None, index_col=False)

        for a_correction in corrections.iterrows():
            city_id = str(a_correction[1][0])
            city_name = a_correction[1][1]
            click.echo(f"Correcting {city_name}")
            for an_entry in geo_id_name[city_id]["indexed_data"]:
                data[an_entry[1]]["addresses"][an_entry[2]]["geonames_city"]["city"] = city_name

        click.echo("Done...\n\n")
        with open(f"{os.path.splitext(data_in)[0]}_cities_corrected.json", "w") as fd:
            json.dump(data,fd)

if __name__ == "__main__":
    correct_dup_cities()
