#!/bin/env python
"""

Administrator
-------------

::

    Usage: citehound_admin.py [OPTIONS] COMMAND [ARGS]...
    
      Citehound -- Administrator.
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      db      Database operations
      fetch   Download data dependencies
      ingest  Data import operations


Database operations
-------------------

::

    Usage: citehound_admin.py db [OPTIONS] COMMAND [ARGS]...
    
      Database operations
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      getschema  Visualises the current schema of the database
      init       Initialises (an empty) Neo4j database with the Citehound...
      link       Runs a probabilistic linking step that links countries and...
      reset      !!!DELETES ALL RECORDS AND REMOVES THE SCHEMA FROM THE...

Fetch external datasets
-----------------------

::

    Usage: citehound_admin.py fetch [OPTIONS] COMMAND [ARGS]...
    
      Download data dependencies
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      mesh  Latest version of the MeSH dataset
      ror   Latest version of the ROR dataset


List and use data loaders
-------------------------

::

    Usage: citehound_admin.py ingest [OPTIONS] COMMAND [ARGS]...
    
      Data import operations
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      data  Selects an importer and imports a data file into Citehound
      ls    Lists the available data importers.

:author: Athanasios Anastasiou
:date: Mar 2023
"""

import os
import sys
import click
import json
import networkx
import citehound

import citehound.models.core
import citehound.models.pubmed
import citehound.models.grid
import citehound.utils
from neomodel import install_all_labels, remove_all_labels

import requests
import datetime


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
def link():
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
    # Get all release data from Zenodo
    try:
        release_data = requests.get("https://zenodo.org/api/records/?communities=ror-data&sort=mostrecent", allow_redirects=True)
        available_releases_data = json.loads(release_data.content.decode("utf8"))
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    try:
        # Get the URLs and their creation dates and sort them in reverse order according to date.
        # In this way, the latest release is the first entry in the list.
        downloads = sorted(list(map(lambda x:{"created":datetime.datetime.fromisoformat(x["created"]),
                                              "url":x["files"][0]["links"]["self"],
                                              "key":x["files"][0]["key"]},
                                    available_releases_data["hits"]["hits"])), 
                           key=lambda x:["created"], 
                           reverse=True)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    
    # Get the actual release file
    try:
        release_file = requests.get(downloads[0]["url"])
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    # Save it to disk
    with open(f"{out_dir}/{downloads[0]['key']}", "wb") as fd:
        fd.write(release_file.content)

    # Done    
    click.echo(f"{downloads[0]['key']} downloaded")


@fetch.command()
@click.option("--out-dir", "-od", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True))
@click.option("--from", "from_year", type=int, default=2002)
@click.option("--to", "to_year", type=int, default=-1)
def mesh(from_year, to_year, out_dir):
    """
    Latest version of the MeSH dataset
    """
    pattern_before_2011 = "1999-2010/xmlmesh/desc"
    pattern_after_2011 = "/xmlmesh/desc"
    download_url = "https://nlmpubs.nlm.nih.gov/projects/mesh/"
    today = datetime.datetime.now().year

    if to_year == -1:
        to_year = today

    if  2002 > from_year > today or from_year < 0:
        click.echo(f"from_year cannot be less than 2002, received {from_year}\n\n")
        sys.exit(-1)

    if to_year > today or to_year < from_year or to_year<-1:
        click.echo(f"to_year cannot be greater than {today} or less than {from_year}.\n\n")
        sys.exit(-1)

    for a_year in range(from_year, to_year):
        if a_year<2011:
            file_path = f"{pattern_before_2011}{a_year}.xml"
        else:
            file_path = f"{a_year}{pattern_after_2011}{a_year}.xml"

        click.echo(f"Working on {a_year}")

        try:
            file_data = requests.get(f"{download_url}{file_path}", allow_redirects=True)
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)

        # Save it to disk
        with open(f"{out_dir}/{os.path.basename(file_path)}", "wb") as fd:
            fd.write(file_data.content)


if __name__ == "__main__":
    citehound_admin()
