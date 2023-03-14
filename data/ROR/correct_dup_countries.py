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
def correct_dup_countries(data_in, corrections_file):
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
        # Get all possible country names
        code_country = {}
        for item_idx, an_item in enumerate(data):
            if an_item["country"]["country_code"] not in code_country:
                code_country[an_item["country"]["country_code"]] = {}
                code_country[an_item["country"]["country_code"]]["indexed_data"] = []
            code_country[an_item["country"]["country_code"]]["indexed_data"].append((item_idx, an_item["country"]))
 
        # If a corrections file is not provided then generate the base for it along with the cached index data
        # Print uniques from each id
        for a_country_code, a_country_data in code_country.items():
            entries = collections.Counter(map(lambda x:x[1]["country_name"], a_country_data["indexed_data"]))
            entry_items = entries.items()
            if len(entry_items)>1:
                code_country[a_country_code]["cached_counts"] = entries
                click.echo(f"{a_country_code}, {','.join(map(lambda x:f'{x[0]}:{x[1]}',entry_items))}")
        
            with open(f"{os.path.splitext(data_in)[0]}_country_cache.json", "w") as fd:
                json.dump(dict(filter(lambda x:"cached_counts" in x[1], code_country.items())), fd)
    else:
        # Load the data file, cached index and corrections file and apply the corrections
        with open(f"{os.path.splitext(data_in)[0]}_country_cache.json", "r") as fd:
            code_country = json.load(fd)

        corrections = pandas.read_csv(corrections_file, header=None, index_col=False)

        for a_correction in corrections.iterrows():
            country_code = a_correction[1][0]
            country_name = a_correction[1][1]
            click.echo(f"Correcting {country_name}")
            for an_entry in code_country[country_code]["indexed_data"]:
                data[an_entry[0]]["country_name"] = country_name

        click.echo("Done...\n\n")
        with open(f"{os.path.splitext(data_in)[0]}_country_corrected.json", "w") as fd:
            json.dump(data,fd)




if __name__ == "__main__":
    correct_dup_countries()
