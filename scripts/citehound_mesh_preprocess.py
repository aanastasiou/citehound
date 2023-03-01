#!/bin/env python
"""
Usage: citehound_mesh_preprocess.py [OPTIONS]

  Citehound -- MESH Importing

  Scans a set of MESH XML files and produces one single JSON tree that
  incorporates all temporal changes in the codes.

Options:
  -i, --input-dir DIRECTORY  Determines the directory containing the
                             downloaded historical MESH XML data.
  -o, --output-file FILE     Determines the output JSON file.
  --help                     Show this message and exit.

:author: Athanasios Anastasiou
:date: April 2018, Dec 2021
"""

# TODO: HIGH, Need to confirm the following note (there is a script about it already).
# It seems to work but when I tried to maintain an updated copy of the term's data, the structure of the tree changed
# and this is worrying.

import os
import sys
import json
import re
import gc
import copy
import glob

from citehound import datainput

import click


@click.command()
@click.option("--input-dir", "-i", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
              default="./", help="Determines the directory containing the downloaded historical MESH XML data.")
@click.option("--output-file", "-o", type=click.Path(file_okay=True, dir_okay=False, resolve_path=True),
              default="MESH_master_tree.json", help="Determines the output JSON file.")
def citehound_mesh_preprocess(input_dir, output_file):
    """
    Citehound -- MESH Importing

    Scans a set of MESH XML files and produces one single JSON tree that incorporates all temporal changes in the
    codes.
    """

    mesh_desc_rule = re.compile("desc(?P<year>[0-9]+)\.xml")

    if os.path.exists(output_file):
        click.echo(f"\n\nThe output file ({output_file}) exists.\nNo action was taken.")
        sys.exit(1)

    # Collect the MESH XML Files
    xml_input_files = sorted(list(map(lambda x: {"file": x[0],
                                                 "year": x[1]["year"]},
                                      filter(lambda x: x[1] is not None,
                                             map(lambda x: (x,
                                                            mesh_desc_rule.search(x)),
                                                 glob.glob(f"{input_dir}/desc*.xml"))))),
                             key=lambda x: x["year"])
    # Process the historical data
    previous_year = {}
    current_master_tree = {}
    for a_file in enumerate(xml_input_files):
        # TODO, HIGH: Log this as an INFO
        # print("Working on {}".format(a_file[1]["file"]))

        mesh_memory_reader = datainput.MeSHDataItemMemoryInsert()
        mesh_memory_reader.read_archive(a_file[1]["file"])

        # Are there any added (new) DUIs?
        # DUIs that are in t current mesh_memory_reader but not in previous_year
        added_duis = set(mesh_memory_reader.memory_storage.keys()) - set(previous_year.keys())
        for an_added_dui in added_duis:
            current_master_tree[an_added_dui] = mesh_memory_reader.memory_storage[an_added_dui]
            # Years this dui was active (from, to).
            # If the item has not been seen before, its from becomes the current year.
            # A none in either (from, to) is interpreted as "to date".
            current_master_tree[an_added_dui]["ValidFromTo"] = {"from": a_file[1]["year"],
                                                                "to": None}
            # Other descriptors dui has been known as (yes, this is possible)
            current_master_tree[an_added_dui]["Aliases"] = [(current_master_tree[an_added_dui]["DescriptorName"],
                                                             {"from": a_file[1]["year"],
                                                              "to": None})]
            current_master_tree[an_added_dui]["TreeNumberHistory"] = dict(list(
                map(lambda x: (x, [{"from": a_file[1]["year"], "to": None}]),
                    current_master_tree[an_added_dui]["TreeNumberList"])))

        # Are there any withdrawn DUIs?
        # DUIs that are in previous_year but not in mesh_memory_reader
        withdrawn_duis = set(previous_year.keys()) - set(mesh_memory_reader.memory_storage.keys())
        for a_withdrawn_dui in withdrawn_duis:
            # Note that you may not have sequential XML files for descriptors.
            current_master_tree[a_withdrawn_dui]["ValidFromTo"]["to"] = xml_input_files[a_file[0] - 1]["year"]

        # All other DUIs will need to be monitored for year-on-year changes to specific elements
        duis_to_update = set(mesh_memory_reader.memory_storage.keys()) - added_duis - withdrawn_duis
        for a_dui in duis_to_update:
            # NOTE DescriptorName CHANGES
            if mesh_memory_reader.memory_storage[a_dui]["DescriptorName"] != previous_year[a_dui]["DescriptorName"]:
                # Note that you may not have sequential XML files for descriptors.
                current_master_tree[a_dui]["Aliases"][-1][1]["to"] = xml_input_files[a_file[0] - 1]["year"]
                current_master_tree[a_dui]["Aliases"].append(
                    (mesh_memory_reader.memory_storage[a_dui]["DescriptorName"],
                     {"from": a_file[1]["year"],
                      "to": None}))
            # NOTE TreeNumber CHANGES
            # TreeNumbers are guaranteed to be unique. Therefore, although TreeNumberList is called a "list" it
            # should really have been a Set.
            if set(mesh_memory_reader.memory_storage[a_dui]["TreeNumberList"]) != \
                    set(previous_year[a_dui]["TreeNumberList"]):
                # TreeNumbers Added
                # They exist in the current year but not in the previous year
                tree_numbers_added = set(mesh_memory_reader.memory_storage[a_dui]["TreeNumberList"]) - \
                                     set(previous_year[a_dui]["TreeNumberList"])
                # TreeNumbers Removed
                tree_numbers_removed = set(previous_year[a_dui]["TreeNumberList"]) - \
                                       set(mesh_memory_reader.memory_storage[a_dui]["TreeNumberList"])

                # Add the new treenumbers
                for a_treenumber_added in tree_numbers_added:
                    # If this tree number has not been assigned in the past, then assign it afresh
                    if not a_treenumber_added in current_master_tree[a_dui]["TreeNumberHistory"]:
                        current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_added] = \
                            [{"from": a_file[1]["year"], "to": None}]
                    else:
                        # If it has been assigned in the past, then add its historic record
                        current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_added].append({
                            "from": a_file[1]["year"], "to": None})

                # Remove the removed treenumbers
                for a_treenumber_removed in tree_numbers_removed:
                    # If there is just one historic record associated with this particular code then assign its end date
                    if len(current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_removed]) == 1:
                        # Note that you may not have sequential XML files for descriptors.
                        current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_removed][0]["to"] = \
                            xml_input_files[a_file[0] - 1]["year"]
                    else:
                        # But, if there are more than one records associated with a code, it means that it
                        # has been re-branched in the past and is now getting re-branched again under the same
                        # tree. This means that the latest record needs to be retrieved and ammended
                        treenumber_historic_index = [index for index, historic_record in enumerate(
                            current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_removed]) if
                                                     historic_record["to"] is None]
                        # TODO: MID, If treenumber_historic_index is not just one for a given code, then this should be an error condition
                        # Note that you may not have sequential XML files for descriptors.
                        current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_removed][
                            treenumber_historic_index[0]]["to"] = xml_input_files[a_file[0] - 1]["year"]
            # Any other change
            current_master_tree[a_dui].update(mesh_memory_reader.memory_storage[a_dui])

        previous_year = copy.deepcopy(mesh_memory_reader.memory_storage)
        # This saves memory
        del(mesh_memory_reader)
        gc.collect()
    # Process finished, save the master tree JSON file
    with open(output_file, "w") as fd:
        # Notice here that the data item reader expects a list format. If the dict is saved as an
        # object within the JSON file then the reader would have to "decode" that.
        # json.dump(list(current_master_tree.items()), fd, indent=4, sort_keys=True, default=str)
        json.dump(current_master_tree, fd, indent=4, sort_keys=True, default=str)


if __name__ == "__main__":
    citehound_mesh_preprocess()
