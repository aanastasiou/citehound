#!/bin/env python
"""
::

    Usage: cmeshprep.py [OPTIONS] COMMAND [ARGS]...
    
      MeSH data preprocessor
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      preprocess  MESH data importing
      visualise   MeSH tree visualisation.

MeSH Preprocessing
------------------

::

    Usage: cmeshprep.py preprocess [OPTIONS]
    
      MESH data importing
    
      Scans a set of MESH XML files and produces one single JSON tree that
      incorporates all temporal changes in the codes.
    
    Options:
      -i, --input-dir DIRECTORY  Determines the directory containing the
                                 downloaded historical MESH XML data.
      -o, --output-file FILE     Determines the output JSON file.
      --help                     Show this message and exit.

MeSH Visualisation
------------------

::

    Usage: cmeshprep.py visualise [OPTIONS] INPUT_FILE TOP_LEVEL_ELEMENT
    
      MeSH tree visualisation.
    
      Samples the main JSON tree that includes all historical changes to produce
      intermediate network and renderings of the tree's evolution for specific
      codes.
    
    Options:
      -b, --year-begin INTEGER
      -e, --year-end INTEGER
      -o, --output-file FILE    Determines the output AND TYPE (via extension)
      --yearly / --not-yearly   Produces one file per year within the year-begin,
                                year-end range.
      --help                    Show this message and exit.


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
import networkx
import random
import matplotlib.pyplot as plt

def get_a_code(chars, code_length=8):
    """
    Returns a random tag that is used to identify nodes

    :param chars: A string containing characters from which the code is formed (e.g. "0123456789ABCDEF")
    :type chars: str
    :param code_length: An integer that determines how many characters long the code would be.
    :type code_length: int (>0)

    :returns: A tag of length code_length containing characters from chars
    :rtype: str
    """

    return "".join([chars[random.randint(0,len(chars)-1)] for a_char in range(0,code_length)])


@click.group()
def citehound_mesh():
    """
    MeSH data preprocessor
    """
    pass

@citehound_mesh.command()
@click.option("--input-dir", "-i", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
              default="./", help="Determines the directory containing the downloaded historical MESH XML data.")
@click.option("--output-file", "-o", type=click.Path(file_okay=True, dir_okay=False, resolve_path=True),
              default="MESH_master_tree.json", help="Determines the output JSON file.")
def preprocess(input_dir, output_file):
    """
    MESH data importing

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

@citehound_mesh.command()
@click.argument("input-file", type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument("top_level_element", type=str)
@click.option("--year-begin", "-b", type=int, help="", default=-1)
@click.option("--year-end", "-e", type=int, help="", default=-1)
@click.option("--output-file", "-o", type=click.Path(file_okay=True, dir_okay=False, resolve_path=True),
              help="Determines the output AND TYPE (via extension)")
@click.option("--yearly/--not-yearly", type=click.BOOL, default=False,
              help="Produces one file per year within the year-begin, year-end range.")
def visualise(input_file, top_level_element, year_begin, year_end, output_file, yearly):
    """
    MeSH tree visualisation.

    Samples the main JSON tree that includes all historical changes to produce intermediate network and renderings of
    the tree's evolution for specific codes.
    """
    # Open the tree file
    with open(input_file, "r") as fd:
        current_master_tree = json.load(fd)

    # Build the reverse lookup of tree numbers to DUIs and also check the earliest and latest dates included in the file
    master_lookup = {}
    year_range = []
    for a_term in current_master_tree.values():
        for a_treenumber in a_term["TreeNumberHistory"]:
            if a_treenumber not in master_lookup:
                master_lookup[a_treenumber] = []
            for a_historic_record in a_term["TreeNumberHistory"][a_treenumber]:
                if a_historic_record["from"] is not None:
                    year_range.append(a_historic_record["from"])
                if a_historic_record["to"] is not None:
                    year_range.append(a_historic_record["to"])
                master_lookup[a_treenumber].append((a_term["DescriptorUI"],
                                                    a_historic_record["from"],
                                                    a_historic_record["to"]))

    # year_counts = sorted(list(collections.Counter(year_range).items()), key=lambda x: x[1])
    year_range = sorted(list(set(year_range)))
    click.echo(f"\n\n{input_file} covers the years {','.join(year_range)}")

    # Anything read from the JSON file is str, convert it to int.
    year_range = list(map(int, year_range))

    if year_begin < 0:
        year_begin = year_range[0]
    if year_end < 0:
        year_end = year_range[-1]

    if year_begin > year_end:
        click.echo(f"\n\nyear-begin({year_begin}) is after year-end({year_end}).\nNo action was taken.\n\n")
        sys.exit(1)

    if not (year_begin in year_range or year_end in year_range):
        click.echo(f"\n\nEither year-begin({year_begin}) or year-end({year_end}) are not within the "
                   f"range covered by {input_file}.\nNo action was taken.\n\n")
        sys.exit(-1)

    # Determine what sort of output is required
    if output_file is not None:
        output_filename, output_ext = os.path.splitext(output_file)
    else:
        output_filename, output_ext = f"visualise_{top_level_element}", "gml"

    # Just make sure that the extension is in lower case to simplify subsequent checks
    output_ext = output_ext.lower()

    if output_ext not in [".gml", ".png"]:
        click.echo(f"\n\nOutput file extension determines format and is expected to be .png or .gml. "
                   f"Received {output_ext}.\nNo action was taken.\n\n")
        sys.exit(1)

    # Now put together the master network
    mesh_dui_network = networkx.DiGraph()

    # TODO: LOW, add a JSON file to customise the appearance of the network (node_colour, edge_colour, thinckness, etc)
    # Establish nodes
    for a_term in current_master_tree.values():
        mesh_dui_network.add_node(a_term["DescriptorUI"],
                                  DescriptorUI=a_term["DescriptorUI"],
                                  Aliases=a_term["Aliases"],
                                  TreeNumberHistory=a_term["TreeNumberHistory"],
                                  ValidFromTo=a_term["ValidFromTo"],
                                  DescriptorName=a_term["DescriptorName"],
                                  node_colour="#FF0000" if a_term["ValidFromTo"]["to"] is not None else "#00FF00")
    # Establish edges (!!ALSO NOTE THAT
    # THE INCOMING AND OUTGOING EDGES TO A WITHDRAWN CODE WOULD ALSO NEED TO BE UPDATED!!)
    for a_term in current_master_tree.values():
        for an_edge in a_term["TreeNumberHistory"].items():
            specialisation_of = ".".join(an_edge[0].split(".")[:-1])
            if specialisation_of != "":
                # Now find the specialisation_of node
                for a_node in master_lookup[specialisation_of]:
                    intermediate_node = f"BRIDGE_{a_term['DescriptorUI']}_{a_node[0]}_{specialisation_of}_" \
                                        f"{a_node[1]}_{a_node[2]}"
                    # mesh_dui_network.add_node(intermediate_node, label=intermediate_node)
                    mesh_dui_network.add_edge(a_term["DescriptorUI"],
                                              intermediate_node,
                                              specialisation_of=specialisation_of,
                                              ValidFromTo=(a_node[1],
                                                           a_node[2] or
                                                           (a_term["ValidFromTo"]["to"] or
                                                            current_master_tree[a_node[0]]["ValidFromTo"]["to"])))

                    mesh_dui_network.add_edge(intermediate_node,
                                              a_node[0],
                                              specialisation_of=specialisation_of,
                                              ValidFromTo=(a_node[1],
                                                           a_node[2] or
                                                           (a_term["ValidFromTo"]["to"] or
                                                            current_master_tree[a_node[0]]["ValidFromTo"]["to"])))

    # Now, filter the network to preserve all nodes that are at the ends of a specialisation_of relationship at a
    # specified time interval
    edges_to_preserve = list(filter(lambda x: x[2]["specialisation_of"].startswith(top_level_element) if "specialisation_of" in x[2] else False, mesh_dui_network.edges(data=True)))
    tree_nodes = set(list(map(lambda x: x[0],
                              edges_to_preserve))).union(set(list(map(lambda x: x[1], edges_to_preserve))))
    # Preserve all nodes that are connected with a bridge node
    # Note here, the network is directed, the following code might appear replicated but it is
    # executed over both directions.
    further_edges_to_preserve = list(filter(lambda x: (x[0].startswith("BRIDGE_") and x[1] in tree_nodes) or
                                                      (x[1].startswith("BRIDGE_") and x[0] in tree_nodes),
                                            mesh_dui_network.edges(data=True)))

    tree_nodes = tree_nodes.union(set(list(map(lambda x: x[0],
                                               further_edges_to_preserve)))).union(set(list(map(lambda x: x[1],
                                                                                                further_edges_to_preserve))))

    further_edges_to_preserve = list(filter(lambda x: (x[0].startswith("BRIDGE_") and x[0] in tree_nodes) or
                                                      (x[1].startswith("BRIDGE_") and x[1] in tree_nodes),
                                            mesh_dui_network.edges(data=True)))

    tree_nodes = tree_nodes.union(set(list(map(lambda x: x[0],
                                               further_edges_to_preserve)))).union(set(list(map(lambda x: x[1],
                                                                                                further_edges_to_preserve))))
    # Get all filtered nodes
    Q = copy.deepcopy(mesh_dui_network.subgraph(tree_nodes))

    # At this point we need to transform the values stored in the keys of the TreeNumberHistory
    # by removing the "illegal" character ("."). DUI identifiers are 3 symbol substrings delimited by ".".
    # For example D01.006.243, would become D01006243.
    for a_node_id, a_node_data in Q.nodes(data=True):
        if "TreeNumberHistory" in a_node_data:
            new_tree_history = {}
            for a_number_key, a_number_value in a_node_data["TreeNumberHistory"].items():
                new_tree_history["".join(a_number_key.split("."))] = a_number_value
            Q.nodes[a_node_id]["TreeNumberHistory"] = new_tree_history

    # TODO: HIGH, Note write_gml here and adjust once this is addressed: https://github.com/networkx/networkx/discussions/5233
    # If a single frame output was requested then create it here and exit.
    if not yearly:
        output_final_filename = f"{output_filename}{output_ext}"
        if output_ext == ".gml":
            networkx.write_gml(Q, output_final_filename, stringizer=repr)

        if output_ext == ".png":
            plt.figure(figsize=(16.5, 11.7))
            pos = networkx.drawing.nx_agraph.graphviz_layout(Q, prog="dot")
            networkx.draw_networkx_nodes(Q, pos)
            networkx.draw_networkx_labels(Q,
                                          pos,
                                          labels=dict(list(map(lambda x: (x,
                                                                          Q.nodes[x][
                                                                              "DescriptorName"] if "DescriptorName" in
                                                                                                   Q.nodes[x] else ""),
                                                               Q.nodes()))),
                                          font_size=4)

            networkx.draw_networkx_edges(Q,
                                         pos,
                                         edge_color="#888888FF")

            plt.title(f"Complete MESH network from {input_file}, for {top_level_element} between the "
                      f"years {year_begin}-{year_end}")
            plt.tight_layout()
            plt.savefig(output_final_filename,
                        dpi=300)
            plt.close()
        click.echo(f"\n\nProduced output in {output_final_filename}")
        sys.exit(0)

    # Fix the positions of the nodes using graphviz
    pos = networkx.drawing.nx_agraph.graphviz_layout(Q, prog="dot")
    for a_year in range(year_begin, year_end):
        output_final_filename = f"{output_filename}_{a_year}{output_ext}"
        F = networkx.DiGraph()
        # F.add_edges_from(list(filter(lambda x:(x[2]["ValidFromTo"][0]<=a_year and (x[2]["ValidFromTo"][1] or 2020)>a_year) if "ValidFromTo" in x[2] else False,
        #                              Q.edges(data=True))))
        F.add_edges_from(list(filter(lambda x: (int(x[2]["ValidFromTo"][0] or 0)<=a_year and int(x[2]["ValidFromTo"][1] or 2020)>a_year) if "ValidFromTo" in x[2] else False,
                                     Q.edges(data=True))))

        if output_ext == ".gml":
            networkx.write_gml(F, output_final_filename, stringizer=repr)

        if output_ext == ".png":
            plt.figure(figsize=(16.5, 11.7))
            networkx.draw_networkx_nodes(F,pos)
            networkx.draw_networkx_labels(F,
                                          pos,
                                          labels=dict(list(map(lambda x: (x,
                                                                          Q.nodes[x]["DescriptorName"] if "DescriptorName" in Q.nodes[x] else ""),
                                                               F.nodes()))),
                                          font_size=4)

            networkx.draw_networkx_edges(F,
                                         pos,
                                         edge_color="#888888FF")

            plt.title(f"Complete MESH network from {input_file}, for {top_level_element} for the year {a_year}")
            plt.tight_layout()
            plt.savefig(output_final_filename,
                        dpi=300)
            plt.close()
        click.echo(f"\n\nProduced output in {output_final_filename}")


if __name__ == "__main__":
    citehound_mesh()
