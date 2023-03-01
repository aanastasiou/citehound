#!/bin/env python
"""
Usage: citehound_mesh_visualise.py [OPTIONS] INPUT_FILE TOP_LEVEL_ELEMENT

  Citehound MESH Visualise.

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
:date: April 2018
"""

import sys
import os
import json
import copy
import networkx
import random
import matplotlib.pyplot as plt
import click


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


@click.command()
@click.argument("input-file", type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument("top_level_element", type=str)
@click.option("--year-begin", "-b", type=int, help="", default=-1)
@click.option("--year-end", "-e", type=int, help="", default=-1)
@click.option("--output-file", "-o", type=click.Path(file_okay=True, dir_okay=False, resolve_path=True),
              help="Determines the output AND TYPE (via extension)")
@click.option("--yearly/--not-yearly", type=click.BOOL, default=False,
              help="Produces one file per year within the year-begin, year-end range.")
def citehound_mesh_visualise(input_file, top_level_element, year_begin, year_end, output_file, yearly):
    """
    Citehound MESH Visualise.

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
    citehound_mesh_visualise()
