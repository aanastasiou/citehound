#!/bin/env python
"""

Administrator
-------------

::


    Usage: cadmin.py [OPTIONS] COMMAND [ARGS]...
    
      Citehound -- Administrator.
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      db      Database operations
      fetch   Download data dependencies
      ingest  Data import operations
      query   Standard query operations over the database.


Database operations
-------------------

::

    Usage: cadmin.py db [OPTIONS] COMMAND [ARGS]...

    Database operations

    Options:
      --help  Show this message and exit.

    Commands:
      create     Create a new data space
      drop       Delete records and (optionally) remove the schema from the...
      getschema  Visualises the current schema of the database
      init       Initialises (an empty) Neo4j database with the Citehound...
      link       Runs a probabilistic linking step that links countries and...
      ls         Lists established database projects
      start      Starts a containerised DBMS on the data space defined by...


Fetch external datasets
-----------------------

::

    Usage: cadmin.py fetch [OPTIONS] COMMAND [ARGS]...
    
      Download data dependencies
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      mesh       Latest version of the MeSH dataset
      pubmedxml  Pubmed result set as XML file
      ror        Latest version of the ROR dataset


List and use data loaders
-------------------------

::

    Usage: cadmin.py ingest [OPTIONS] COMMAND [ARGS]...
    
      Data import operations
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      data  Selects an importer and imports a data file into Citehound
      ls    Lists the available data importers.

List, update query collections
------------------------------

::

    Usage: cadmin.py query [OPTIONS] COMMAND [ARGS]...
    
      Manage query collections and run standardised queries.
    
    Options:
      --help  Show this message and exit.
    
    Commands:
      init  Initialises a query collection in the database
      ls    List all available queries within a collection
      rm    Remove a query collection from the database.
      run   Select and run a query from a collection.

:author: Athanasios Anastasiou
:date: Mar 2023
"""

import os
import sys
import re
import click
import json
import networkx

from citehound import CM
import citehound.utils
from citehound import std_queries
from neomodel import install_all_labels, remove_all_labels
import neomodel
import neoads

import requests
import datetime
from xml.etree import ElementTree
import time

import yaml
import shutil
import subprocess

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
def ls():
    """
    Lists established database projects
    """
    # Check that the environment variables are set
    if "CITEHOUND_DATA" not in os.environ:
        click.echo("ERROR: CITEHOUND_DATA not set")
        sys.exit(-1)

    # Get all directories under CITEHOUND_DATA
    for a_dir in os.listdir(f"{os.environ['CITEHOUND_DATA'].rstrip('/')}/"):
        if not a_dir.startswith('.') and os.path.isdir(f"{os.environ['CITEHOUND_DATA'].rstrip('/')}/{a_dir}"):
            click.echo(f"{a_dir}")


@db.command()
@click.argument("project-name", type=str)
def start(project_name):
    """
    Starts a containerised DBMS on the data space defined by "project_name"
    """
    # Validate project name
    project_name_val_rule = re.compile("[a-zA-Z][a-zA-Z_0-9]+")

    if not project_name_val_rule.match(project_name):
        click.echo(f"ERROR: project-name should start with a letter and contain only letters, numbers and the '_' character. Received:{project_name}\n")
        sys.exit(-1)

    # Check that the environment variables are set
    if "CITEHOUND_DATA" not in os.environ:
        click.echo("ERROR: CITEHOUND_DATA not set")
        sys.exit(-1)

    if "CITEHOUND_CONTAINER_BIN" not in os.environ:
        click.echo("ERROR: CITEHOUND_CONTAINER_BIN not set")
        sys.exit(-1)

    if "CITEHOUND_CONTAINER_IMG" not in os.environ:
        click.echo("ERROR: CITEHOUND_CONTAINER_IMG not set")
        sys.exit(-1)

    project_path = f"{os.environ['CITEHOUND_DATA'].rstrip('/')}/{project_name}"

    # Check that the project path exists
    if not (os.path.exists(f"{project_path}/data") and os.path.exists(f"{project_path}/logs")):
        click.echo(f"ERROR: Path {project_path} does not exist. No action was taken")
        sys.exit(-1)

    process_str = f"{os.environ['CITEHOUND_CONTAINER_BIN']} run --restart always --publish=7474:7474 --publish=7687:7687 --env NEO4J_AUTH={os.environ['NEO4J_USERNAME']}/{os.environ['NEO4J_PASSWORD']} --volume={project_path}/data:/data --volume={project_path}/logs:/logs {os.environ['CITEHOUND_CONTAINER_IMG']}"

    p = subprocess.Popen(process_str,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         shell=True)

    click.echo(f"{project_name} started up.")

@db.command()
@click.argument("project-name", type=str)
@click.option("--based-on", "-b", type=str, help="Copies across the data space from another project")
def create(project_name, based_on):
    """
    Create a new data space
    """
    # Validate project name
    project_name_val_rule = re.compile("[a-zA-Z][a-zA-Z_0-9]+")

    if not project_name_val_rule.match(project_name):
        click.echo(f"ERROR: project-name should start with a letter and contain only letters, numbers and the '_' character. Received:{project_name}\n")
        sys.exit(-1)

    # Check that the environment variables are set
    if "CITEHOUND_DATA" not in os.environ:
        click.echo("ERROR: CITEHOUND_DATA not set")
        sys.exit(-1)

    # Check that the path does not exist
    project_path = f"{os.environ['CITEHOUND_DATA'].rstrip('/')}/{project_name}"
        
    if os.path.exists(project_path):
        click.echo(f"ERROR: Path {project_path} exists. No action was taken")
        sys.exit(-1)

    if based_on is not None:
        # Validate based_on
        if not project_name_val_rule.match(based_on):
            click.echo(f"ERROR: based-on should start with a letter and contain only letters, numbers and the '_' character. Received:{based_on}\n")
            sys.exit(-1)
        project_based_on = f"{os.environ['CITEHOUND_DATA'].rstrip('/')}/{based_on}"
        # Make sure it exists
        if not os.path.exists(project_based_on):
            click.echo(f"ERROR: based_on project path ({project_based_on}) does not exist. No action was taken")
            sys.exit(-1)

    # At this point we are ready to create a new project
    # Make new directories as required
    os.makedirs(f"{project_path}/data", exist_ok=True)
    os.makedirs(f"{project_path}/logs", exist_ok=True)

    # Copy files across if required
    if based_on is not None:
        shutil.copytree(project_based_on, project_path, dirs_exist_ok=True)

    click.echo(f"Project {project_name} created.")


@db.command()
@click.argument("output-format", type=click.Choice(["graphml", "dot"], case_sensitive=False),)
@click.option("--schema-ext/--no-schema-ext",
              type=click.BOOL,
              default=False,
              help="Enables any extensions to the base Citehound schema")
@click.option("--isolated/--no-isolated",
              type=click.BOOL,
              default=False,
              help="Drops any entities that appear to not be connected with others in the current schema.")
def getschema(output_format, schema_ext, isolated):
    """
    Visualises the current schema of the database
    """
    def filter_dict_attr(a_dict, attrs_to_drop):
        return dict(filter(lambda x: x[0] not in attrs_to_drop, a_dict.items()))

    schema_data = citehound.IM.cypher_query("call db.schema.visualization", resolve_objects=False, result_as="raw")

    # Build the network first
    network_data = schema_data[0]
    net_ob = networkx.DiGraph()
    for a_node in network_data[0]:
        net_ob.add_node(a_node.id,
                        labels=",".join(a_node.labels),
                        nname=a_node._properties["name"],
                        #indexes=",".join(a_node._properties["indexes"]),
                        #constraints=",".join(a_node._properties["constraints"])
                        )

    for a_relationship in network_data[1]:
        net_ob.add_edge(a_relationship.start_node.id,
                        a_relationship.end_node.id, type=a_relationship.type)

    if not isolated:
        net_ob.remove_nodes_from(list(filter(lambda x: net_ob.degree(x) == 0, net_ob.nodes())))

    if output_format == "graphml":
        networkx.write_graphml(net_ob, sys.stdout)

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
        networkx.drawing.nx_pydot.write_dot(net_ob, sys.stdout)


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
    bim.link_sets_of_entities("match (aCountry:Country) return toLower(aCountry.name) as theIndex, aCountry as theNode",
                               "match (an_affiliation:PubmedAffiliation) return toLower(an_affiliation.original_affiliation) as theIndex, an_affiliation as theNode",
                               COUNTRY_ASSOCIATION_LABEL,
                               session_id="MySessionStep1",
                               pre_processing_function = citehound.utils.affiliation_standardisation,
                               perc_entries_right = 0.95)

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
        bim.link_sets_of_entities(
            f"match (a:Institute)-[:IN_CITY]-(:City)-[:IN_COUNTRY]-(b:Country{{name:'{aCountry}'}}) return distinct toLower(a.name) as theIndex,a as theNode",
            f"match (a:PubmedAffiliation)-[:ASSOCIATED_WITH{{rel_label:'FROM_COUNTRY'}}]-(b:Country{{name:'{aCountry}'}}) return distinct toLower(a.original_affiliation) as theIndex, a as theNode",
            INSTITUTE_ASSOCIATION_LABEL,
            session_id="MySessionStep2",
            pre_processing_function=citehound.utils.affiliation_standardisation,
            perc_entries_right=0.95)

    # Now grab those articles which where not connected NEITHER WITH A COUNTRY OR UNIVERSITY
    bim.link_sets_of_entities("match (a:Institute) return distinct toLower(a.name) as theIndex,a as theNode",
                               "match (a:PubmedAffiliation) where not (a)-[:ASSOCIATED_WITH{rel_label:'FROM_COUNTRY'}]-() and not (a)-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-() return distinct toLower(a.original_affiliation) as theIndex, a as theNode",
                               INSTITUTE_ASSOCIATION_LABEL,
                               session_id="MySessionStep3",
                               pre_processing_function=citehound.utils.affiliation_standardisation,
                               perc_entries_right=0.95)

    click.echo("Finished linking.")


@db.command()
@click.argument("what-to-drop", type=click.Choice(["all", "all-and-labels", "article-data", "ror"]))
@click.option("--confirm", is_flag=True, help="Confirms that the user indeed wishes to drop a category of records")
def drop(what_to_drop, confirm):
    """
    Delete records and (optionally) remove the schema from the database.
    """
    if (what_to_drop in ["all", "all-and-labels"]):
        pre_action = "Dropping all records and reseting the database"
        post_action = "\n\nThe database has been reset.\n"
        action = "MATCH (a) DETACH DELETE (a)"

    if (what_to_drop == "article-data"):
        pre_action = "Dropping article data (Articles, Authors and Affiliations)"
        post_action = "\n\nArticle data removed.\n"
        action = "MATCH (a) WHERE 'Article' IN labels(a) OR 'Author' IN labels(a) OR 'Affiliation' IN labels(a) DETACH DELETE a"

    if (what_to_drop == "ror"):
        pre_action = "Dropping all ROR records."
        post_action = "\n\nROR data removed.\n"
        action = "MATCH (a) WHERE 'City' IN labels(a) OR 'Country' IN labels(a) OR 'Institute' IN labels(a) DETACH DELETE a"

    if not confirm:
        click.echo(f"Please append option --confirm to actually drop {what_to_drop} records")
    else:
        with neomodel.db.transaction:
            click.echo(pre_action)
            citehound.IM.cypher_query(action)
            click.echo(post_action)

            if (what_to_drop == "all-and-labels"):
                neomodel.remove_labels()
                click.echo("Labels removed.\n")


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
@click.option("--out-dir", "-od", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True), default="./")
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


@fetch.command()
@click.argument("pmid_file", type=click.Path(exists=True, file_okay=True, dir_okay=False))
def pubmedxml(pmid_file):
    """
    Pubmed result set as XML file. 

    PMID_FILE should be a text file with one PMID per line. 
    The XML result set is returned on stdout.
    """
    if "NCBI_API_KEY" not in os.environ:
        # If a key is not available, medline limits calls to 1 per second.
        inter_call_delay = 1
    else:
        # otherwise this limit is raised to 10 calls per second.
        inter_call_delay = 0.1

    BATCH_SIZE = 300
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&api_key={os.environ['NCBI_API_KEY']}&rettype=medline&retmode=xml&id="
    # Get the PMID data
    # PMID data should be provided in one row per article (PMID) in a text file
    with open(pmid_file) as fd:
        data = list(map(lambda x: x.rstrip(),fd.readlines()))

    # Create the batch requests and format them as coma separated lists
    data_batches = [",".join(data[k:k+BATCH_SIZE]) for k in range(0, len(data), BATCH_SIZE)]
    pubmed_xml_data = None
    for a_batch in data_batches:
        try:
            xml_data = requests.get(url+a_batch, allow_redirects=True)
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        if pubmed_xml_data is None:
            pubmed_xml_data = ElementTree.fromstring(xml_data.content.decode("utf8"))
        else:
            pubmed_xml_data.extend(ElementTree.fromstring(xml_data.content.decode("utf8")))
        time.sleep(inter_call_delay)

    click.echo(ElementTree.tostring(pubmed_xml_data, 
                                    encoding="utf8", 
                                    method="xml",))

@citehound_admin.group()
def query():
    """
    Manage query collections and run standardised queries.
    """
    pass


@query.command()
@click.option("--collection-file", "-f", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option("--re-init", "-r", is_flag=True)
def init(collection_file, re_init):
    """
    Initialises a query collection in the database

    If a --collection_file is not provided and STD_QUERIES does not exist, it is created.
    """
    if not collection_file:
        collection_name = "STD_QUERIES"
        query_data = std_queries.STD_QUERIES

    else:
        collection_name = os.path.splitext(os.path.basename(collection_file))[0].upper()

        # Check the form of the list name
        if re.compile("^[A-Z_][A-Z_]*$").match(collection_name) is None:
            click.echo(f"The file name should be composed of capital letters and the '_' character, received {collection_name}")
            sys.exit(-1)

        # Check that the CSV at least has three pre-defined columns
        with open(collection_file, "r") as fd:
            query_data = yaml.safe_load(fd)

        defined_attributes = set()
        for a_qry_name, a_qry_dat in query_data.items():
            defined_attributes |= set(a_qry_dat.keys())

        if len(defined_attributes) !=2 and not ("description" in defined_attributes or "cypher" in defined_attributes):
               click.echo(f"The yaml file must have three columns named QueryName, Description, Cypher.")
               sys.exit(-1)

    # Let's interact with the database
    IM = CM._mem_manager

    with neomodel.db.transaction:
        # Check if the query collections exist
        try:
            query_collection = IM.get_object("QUERY_COLLECTIONS")
        except neoads.exception.ObjectNotFound as e:
            # Initialise the top level QUERY_COLLECTIONS map
            query_collection = neoads.AbstractMap(name="QUERY_COLLECTIONS").save()

        # Check if the particular collection is already defined
        if neoads.CompositeString(collection_name) in query_collection:
            # If the list exists then check if it should be re-initialised
            if re_init:
                del(query_collection[neoads.CompositeString(collection_name)])
                # Do a garbage collection step here
                IM.garbage_collect()
                the_map = neoads.AbstractMap().save()
                the_key = neoads.CompositeString(collection_name).save() 
                query_collection[the_key] = the_map
            else:
                click.echo(f"List {collection_name} already exists.")
                sys.exit(-1)
        else:
            # If the list does not exist and it was asked to be recreated then this should
            # cause an error.
            if re_init:
                click.echo(f"Collection {collection_name} cannot be re-initialised because it does not exist")
                sys.exit(-1)
            # Otherwise go ahead and create it
            the_map = neoads.AbstractMap().save()
            # Add it to the collection
            the_key = neoads.CompositeString(collection_name).save() 
            query_collection[the_key] = the_map

        # At this point, the_map has been initialised in one or another way.
        # Populate it

        query_key = neoads.CompositeString("query").save()
        desc_key = neoads.CompositeString("description").save()
        # Add items
        for a_query_name, query_dta in query_data.items():
            # Create the entries for each 
            q_name_ob = neoads.CompositeString(a_query_name).save()
            q_value_ob = neoads.CompositeArrayObjectDataFrame(query_dta["cypher"]).save()
            q_desc_ob = neoads.CompositeString(query_dta["description"]).save()
            # The inner map has to be populated first
            q_new_map = neoads.AbstractMap().save()
            q_new_map[query_key] = q_value_ob
            q_new_map[desc_key] = q_desc_ob
            # The map can now be attached to the outer map
            the_map[q_name_ob] = q_new_map


@query.command()
@click.option("--verbose", "-v", is_flag=True, help="Includes actual (cypher) queries in the listing")
@click.option("--collection-name", "-n", type=str, help="List the contents of a particular query collection, default is STD_QUERIES if it has been installed")
def ls(verbose, collection_name):
    """
    List all available queries within a collection
    """
    IM = CM._mem_manager
    # TODO: HIGH, Perform a very typical validation for [A-Z_][A-Z_]* pattern on collection_name
    collection_name = collection_name.upper() if collection_name else None

    # Check if the query collections exist
    try:
        query_collection = IM.get_object("QUERY_COLLECTIONS")
    except neoads.exception.ObjectNotFound as e:
        click.echo("Query collections have not been initialised on this database, please see 'query init'")
        sys.exit(-1)

    # If a collection name has not been provided, list all collections
    if collection_name is None:
        click.echo("Collection, Number of queries")
        for a_key in list(query_collection.keys):
            click.echo(f"{a_key.value}, {len(query_collection[a_key])}")
        sys.exit(0)

    # Otherwise, check if the specified collection name exists.
    if neoads.CompositeString(collection_name) not in query_collection:
        click.echo(f"{collection_name} has not been installed in this database yet.\n")
        sys.exit(-1)

    # The collection exists, go ahead and list its contents.
    q_map = query_collection[neoads.CompositeString(collection_name)]
    # Get all contents to memory
    list_contents={}
    for a_key in list(q_map.keys):
        list_contents[a_key.value] = {"description":q_map[a_key][neoads.CompositeString('description')].value,
                                               "cypher":q_map[a_key][neoads.CompositeString('query')].value}

    # Decide what and how to "print"
    if verbose:
        yaml.dump(list_contents, sys.stdout)
    else:
        click.echo("QueryName, Description")
        for a_key, a_val in list_contents.items():
            click.echo(f"{a_key}, {a_val['description']}")
 

@query.command()
@click.argument("query-name", type=str)
@click.option("--collection-name", "-n", type=str, default="STD_QUERIES", help="Choose the query from a particular list, default is STD_QUERIES if it has been installed")
@click.option("--parameter", "-p", multiple=True)
def run(query_name, collection_name, parameter):
    """
    Select and run a query from a collection.
    """

    # TODO: HIGH, Add validation to collection_name here for [A-Z_][A-Z_]*
    collection_name = collection_name.upper()

    IM = CM._mem_manager

    # Check if the query collections exist
    try:
        query_collection = IM.get_object("QUERY_COLLECTIONS")
    except neoads.exception.ObjectNotFound as e:
        click.echo("Query collections have not been initialised on this database, please see 'query init'")
        sys.exit(-1)

    # Get the collection
    if neoads.CompositeString(collection_name) in query_collection:
        q_map = query_collection[neoads.CompositeString(collection_name)]
    else:
        click.echo(f"{collection_name} has not been installed in this database yet.\n")
        sys.exit(-1)

    # Package parameters
    params = {}
    for a_param in parameter:
        if "=" not in a_param:
            click.echo(f"Parameters are expected as -p param=param_value. Please revise {a_param} adn try again")
            sys.exit(-1)
        key, value = a_param.split("=")
        if not (value.startswith("'") and value.endswith("'")):
            try:
                value = int(value)
            except ValueError:
                click.echo(f"Parameters without single quotes are assumed to be nummeric, please revise {a_param} and try again")
                sys.exit(-1)
        params[key] = value

    # Check if the query exists.
    if neoads.CompositeString(query_name.upper()) in q_map.keys_set[0]:
        # Run the query itself and return results
        z = q_map[neoads.CompositeString(query_name.upper())][neoads.CompositeString("query")].execute(params=params)
        z.to_csv(sys.stdout, index=False)
    else:
        click.echo(f"Query {query_name.upper()} does not exist. Please run 'query ls' to see all available queries.")


@query.command()
@click.argument("collection-name", type=str,)
@click.option("--confirm", is_flag=True, help="Confirms that the user indeed wishes to delete this list")
def rm(collection_name, confirm):
    """
    Remove a query collection from the database.
    """

    # TODO: HIGH, Add validation to collection_name here for [A-Z_][A-Z_]*
    collection_name = collection_name.upper()
    IM = CM._mem_manager

    with neomodel.db.transaction:
        # Check if the query collections exist
        try:
            query_collection = IM.get_object("QUERY_COLLECTIONS")
        except neoads.exception.ObjectNotFound as e:
            click.echo("Query collections have not been initialised on this database, please see 'query init'")
            sys.exit(-1)


        # Check if the specified collection exists
        if neoads.CompositeString(collection_name) in query_collection:
            q_map = query_collection[neoads.CompositeString(collection_name)]
        else:
            click.echo(f"{collection_name} has not been installed in this database yet. Please see 'query ls' for a list of the installed collections. \n")
            sys.exit(-1)

        # If the collection exists, then delete it (if the action is confirmed).
        if confirm:
            q_map.destroy()
            del(query_collection[neoads.CompositeString(collection_name)])
            IM.garbage_collect()
        else:
            click.echo(f"{collection_name} exists and can be deleted. If you wish to delete it, please re-run the exact same rm command, appending '--confirm'")


if __name__ == "__main__":
    citehound_admin()
