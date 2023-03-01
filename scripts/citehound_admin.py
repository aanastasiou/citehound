#!/bin/env python
"""
Usage: citehound_admin.py [OPTIONS] COMMAND [ARGS]...

  Citehound -- Administrator.

Options:
  --help  Show this message and exit.

Commands:
  db-getschema  Visualises the current schema of the database
  db-init       Initialises (an empty) Neo4j database with the Citehound...
  db-problink   Runs a probabilistic linking step that links countries...
  db-reset      !!!DELETES ALL RECORDS AND REMOVES THE SCHEMA FROM THE...
  import-data   Selects an importer and imports a data file into Citehound
  import-ls     Lists the available data importers.


:author: Athanasios Anastasiou
:date: Jan 2018, May 2018, Dec 2021
"""

import os
import click
import json
import networkx
import citehound

import citehound.models.core
import citehound.models.pubmed
import citehound.models.grid
import citehound.utils
from neomodel import install_all_labels, remove_all_labels

import urllib.request


@click.group()
def citehound_admin():
    """
    Citehound -- Administrator.

    """
    pass


@citehound_admin.group()
def db():
    """
    Database operations
    """
    pass

@db.command()
@click.argument("output-filename", type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
@click.option("--output-format", "-f",
              type=click.Choice(["json", "gml", "dot"], case_sensitive=False),
              help="Determine the output format",
              default="json")
@click.option("--schema-ext/--no-schema-ext",
              type=click.BOOL,
              default=False,
              help="Enables any extensions to the base Citehound schema")
@click.option("--isolated/--no-isolated",
              type=click.BOOL,
              default=False,
              help="Drops any entities that appear to not be connected with others in the current schema.")
def getschema(output_filename, output_format, schema_ext, isolated):
    """
    Visualises the current schema of the database
    """
    def filter_dict_attr(a_dict, attrs_to_drop):
        return dict(filter(lambda x: x[0] not in attrs_to_drop, a_dict.items()))

    final_output_filename = os.path.splitext(output_filename)[0]
    schema_data = citehound.IM.cypher_query("call db.schema.visualization", resolve_objects=False, result_as="raw")
    if output_format == "json":
        with open(f"{final_output_filename}.json", "w") as fd:
            json.dump(schema_data, fd, indent=4)
    else:
        # Build the network first
        network_data = schema_data[0]
        net_ob = networkx.DiGraph()
        for a_node in network_data[0]:
            net_ob.add_node(a_node.id,
                            labels=tuple(a_node.labels),
                            nname=a_node._properties["name"],
                            indexes=a_node._properties["indexes"],
                            constraints=a_node._properties["constraints"]
                            )

        for a_relationship in network_data[1]:
            net_ob.add_edge(a_relationship.start_node.id,
                            a_relationship.end_node.id, type=a_relationship.type, **a_relationship._properties)
        if not isolated:
            net_ob.remove_nodes_from(list(filter(lambda x: net_ob.degree(x) == 0, net_ob.nodes())))

        if output_format == "gml":
            networkx.write_gml(net_ob, f"{final_output_filename}.gml", stringizer=repr)
        elif output_format == "dot":
            # Re-format the network
            for a_node_idx, a_node_data in net_ob.nodes(data=True):
                a_node_data["label"] = f"{a_node_data['nname']}"
            for a_rel_node_begin, a_rel_node_end, a_rel_data in net_ob.edges(data=True):
                a_rel_data["label"] = f"{a_rel_data['type']}"

            names_to_remove = ["AssociableItem",
                               "PersistentElement",
                               "ElementDomain"]
            if schema_ext:
                names_to_remove.extend(["Article", "Author", "Affiliation"])
            else:
                names_to_remove.extend(list(map(lambda x: x[1]["nname"],
                                                filter(lambda x: x[1]["nname"] not in ["Article",
                                                                                       "Author",
                                                                                       "Affiliation",
                                                                                       "Institute",
                                                                                       "InstituteType",
                                                                                       "City",
                                                                                       "Country"],
                                                       net_ob.nodes(data=True)))))

            net_ob.remove_nodes_from(list(map(lambda x: x[0],
                                              filter(lambda x: x[1]["nname"] in names_to_remove,
                                                     net_ob.nodes(data=True)))))
            networkx.drawing.nx_pydot.write_dot(net_ob, f"{final_output_filename}.dot")


@db.command()
def problink():
    """
    Runs a probabilistic linking step that links countries and institutions.

    The probabilistic linking is executed after "blocking" against the Country entities:
        1. Link all possible affiliations to countries.
        2. Given a Country, retrieve its institutions and link them to those of GRID.
    """
    COUNTRY_ASSOCIATION_LABEL = "FROM_COUNTRY"
    INSTITUTE_ASSOCIATION_LABEL = "FROM_INSTITUTE"

    bim = citehound.IM

    # First, match and link countries
    bim.probLinkSetsOfEntities("match (aCountry:Country) return toLower(aCountry.name) as theIndex, aCountry as theNode",
                               "match (an_affiliation:PubmedAffiliation) return toLower(an_affiliation.original_affiliation) as theIndex, an_affiliation as theNode",
                               COUNTRY_ASSOCIATION_LABEL,
                               sessionID="MySessionStep1",
                               preProcessingFunction = citehound.utils.affiliation_standardisation,
                               percEntriesRIGHT=0.95)

    # Now, for each country that actually matched, get its institutions and try to match institutions too
    matched_countries = bim.cypher_query(
        "match (a:PubmedAffiliation)-[:ASSOCIATED_WITH{rel_label:'FROM_COUNTRY'}]-(b:Country) return distinct b.name as theIndex, b as theNode",
        result_as="dict",
        resolve_objects=True)

    # For each country
    for aCountry in matched_countries:
        click.echo(f"Working on {aCountry}")
        # Grab the affiliations that are associated with that particular country
        # Grab the institutions that we know exist within that paritcular country
        # Link the affiliations to institutes.
        # REMEMBER SEMANTICS. Link by looking for LEFT in RIGHT. Therefore LEFT:Institutes, RIGHT:Affiliations
        bim.probLinkSetsOfEntities(
            f"match (a:Institute)-[:IN_CITY]-(:City)-[:IN_COUNTRY]-(b:Country{{name:'{aCountry}'}}) return distinct toLower(a.name) as theIndex,a as theNode",
            f"match (a:PubmedAffiliation)-[:ASSOCIATED_WITH{{rel_label:'FROM_COUNTRY'}}]-(b:Country{{name:'{aCountry}'}}) return distinct toLower(a.original_affiliation) as theIndex, a as theNode",
            INSTITUTE_ASSOCIATION_LABEL,
            sessionID="MySessionStep2",
            preProcessingFunction=citehound.utils.affiliation_standardisation,
            percEntriesRIGHT=0.95)

    # Now grab those articles which where not connected NEITHER WITH A COUNTRY OR UNIVERSITY
    bim.probLinkSetsOfEntities("match (a:Institute) return distinct toLower(a.name) as theIndex,a as theNode",
                               "match (a:PubmedAffiliation) where not (a)-[:ASSOCIATED_WITH{rel_label:'FROM_COUNTRY'}]-() and not (a)-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-() return distinct toLower(a.original_affiliation) as theIndex, a as theNode",
                               INSTITUTE_ASSOCIATION_LABEL,
                               sessionID="MySessionStep3",
                               preProcessingFunction=citehound.utils.affiliation_standardisation,
                               percEntriesRIGHT=0.95)

    click.echo("Finished linking.")


@db.command()
@click.option("--n_items", type=int, )
def reset(n_items):
    """
    !!!DELETES ALL RECORDS AND REMOVES THE SCHEMA FROM THE CURRENT DATABASE!!!
    """
    n_items_in_db = citehound.IM.number_of_items_in_db
    if n_items != n_items_in_db:
        click.echo("\n\nSafety verification FAILED.\nNo action was taken.\n\n")
    else:
        citehound.IM.cypher_query("MATCH (a) DETACH DELETE (a)")
        remove_all_labels()
        click.echo("\n\nThe database has been reset.\n")


@db.command()
def init():
    """
    Initialises (an empty) Neo4j database with the Citehound schema.
    """
    n_items_in_db = citehound.IM.number_of_items_in_db
    if n_items_in_db > 0:
        click.echo(f"\n\nThe database contains {n_items_in_db} items.\nNo action was taken.\n\n")
    else:
        install_all_labels()
        click.echo("\n\nThe database has been initialised.\n")


@citehound_admin.group()
def ingest():
    """
    Data import operations
    """
    pass

@ingest.command()
def ls():
    """
    Lists the available data importers.
    """
    for an_importer in citehound.IM.importers.values():
        click.echo(f"{an_importer['name']}\t{an_importer['description']}")


@ingest.command()
@click.argument("dataset_type", type=str)
@click.argument("dataset_path", type=click.Path(exists=True))
def data(dataset_type, dataset_path):
    """
    Selects an importer and imports a data file into Citehound
    """
    citehound.IM.import_data(dataset_type.upper(), dataset_path)

@citehound_admin.group()
def fetch():
    """
    Download data dependencies
    """
    pass

@fetch.command()
@click.option("--out-dir", "-od", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True))
def ror(out_dir):
    """
    Latest version of the ROR dataset
    """
    with urllib.request.urlopen("https://zenodo.org/api/records/?communities=ror-data&sort=mostrecent") as rp:
        available_releases_data = json.loads(rp.read().decode("utf8"))
    # Get the URLs and their creation dates and sort them in reverse order according to date
    downloads = sorted(list(map(lambda x:{"created":x["created"],
                                          "url":x["files"][0]["links"]["self"]},
                                available_releases_data["hits"]["hits"])), 
                       key=lambda x:["created"], 
                       reverse=True)

    click.echo(downloads)

@fetch.command()
def mesh():
    """
    Latest version of the MeSH dataset
    """
    pass



if __name__ == "__main__":
    citehound_admin()
