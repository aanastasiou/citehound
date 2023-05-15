"""
Citehound core functionality.

:author: Athanasios Anastasiou
:date: Mar 2023
"""

import os
import sys
import uuid
import re
import difflib
import datetime
import copy

import neomodel
from . import exceptions
from . import batchprocess
from . import datainput

from neoads import MemoryManager

import collections

import pandas

import warnings


# TODO: HIGH, Document these functions.
def rptr(a_message):
    # logging.info(a_message)
    sys.stdout.write(f"{a_message}{''.join([' '] * (40 - len(a_message)))}{datetime.datetime.now()}\n")


class CitehoundManager:
    class __CitehoundManager:
        """
        The main object via which all operations are carried out on the system
        """

        def __init__(self, connection_uri=None, uname=None, pword=None, host="localhost", port=7687):
            """
            Initialise the main object.

            Note: If none of the expected configuration parameters are provided, the constructor will try
            to initialise the object via the connection_uri environment variable. If that fails, it will
            try to initialise it via the username and password data and if that fails, then it will
            give up with an appropriate exception.

            :param connection_uri: String, a connection URI supplied by the user
            :param uname: String, A username
            :param pword: String, A password
            :param host: String, The host the server is running on
            :param port: Integer, The port number the server is running on
            """
            # # Setup the logging
            # logging.basicConfig(format="%(levelname)s:%(name)s:%(asctime)s:%(message)s", datefmt="%m/%d/%Y %I:%M:%S %p",
            #                     filename="insightql.log",
            #                     level=logging.INFO)
            conn_uri = None
            self._data_importers = {}
            if "NEO4J_BOLT_URL" not in os.environ:
                if "NEO4J_USERNAME" not in os.environ and \
                   "NEO4J_PASSWORD" not in os.environ:
                    warnings.warn("The NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_BOLT_URI environment variables are not set. Cannot connect to database")
                else:
                    uname = uname or os.environ["NEO4J_USERNAME"]
                    pword = pword or os.environ["NEO4J_PASSWORD"]
                    conn_uri = f"bolt://{uname}:{pword}@{host}:{port}"
            else:
                conn_uri = connection_uri or os.environ["NEO4J_BOLT_URL"]
            self._connection_URI = conn_uri
            if self._connection_URI is not None:
                neomodel.db.set_connection(self._connection_URI)
                self._mem_manager = MemoryManager(connection_uri = self._connection_URI, reset_connection=False)
            else:
                # TODO: HIGH, Raise exception as it is impossible to initialise the required objects
                pass


        @property
        def importers(self):
            return self._data_importers

        @property
        def connection_uri(self):
            """
            Returns a connection URI for the neo4j server
            :return:
            """
            return self._connection_URI

        # TODO: MID, This could be parametrised with an abstract class to count specific objects.
        @property
        def number_of_items_in_db(self):
            return neomodel.db.cypher_query("MATCH (a) RETURN COUNT(a) AS OBJ_COUNT")[0][0][0]

        def register_importer(self, an_importer):
            """
            Registers a data importer which will then be used to bring data into the system
            :param an_importer:
            :return:
            """
            if an_importer["name"] in self._data_importers:
                raise exception.ManagerError(f"Data importer {an_importer['name']} already defined")

            self._data_importers[an_importer["name"]] = copy.deepcopy(an_importer)

        def import_data(self, importer_name, *args, **kwargs):
            """
            Imports data using a specific importer
            :param importer_name:
            :param args:
            :param kwargs:
            :return:
            """
            self._data_importers[importer_name]["object"].read_archive(*args, **kwargs)

        def cypher_query(self, query, params=None, result_as="list", resolve_objects=True):
            """
            Executes the query and returns either a list of dictionaries or an indexed list of dictionaries or a pandas.DataFrame.
            If noCasting is False, "Nodes" are cast to associables

            :param query: A CYPHER Query to send to Neo4j
            :type query: str
            :param params: Parameters of the CYPHER query
            :type params: str
            :param result_as: Try and convert the return value from the query to one of list, dict, pandas, raw, with
                              raw returning the exact result of the query untreated.
            :type result_as: str
            :param resolve_objects: Whether to try and resolve return results to BibInsight objects.
            :type resolve_objects: bool

            :return: Query results in the requested format.
            :rtype: list, dict, pandas.DataFrame
            """
            items, attr = neomodel.db.cypher_query(query, params=params, resolve_objects=resolve_objects)
            toRet = None
            if result_as == "list":
                # If a list is requested, you return a simple list of dictionaries which allow accessors of the form myList[0]["someNode"]
                toRet = list(map(lambda x: dict(zip(attr, x)), items))
            elif result_as == "dict":
                # If a dict is requested, you return a dict of dictionaries
                toRet = dict(map(lambda x: (x[0], dict(zip(attr[1:], x[1:]))), items))
            elif result_as == "pandas":
                # If the return is a pandas dataframe then noCasting is ignored
                toRet = pandas.DataFrame(columns=attr, data=items, index=None)
            elif result_as == "raw":
                # In the case of Raw, the return value is simply returned.
                toRet = items
            else:
                raise NotImplementedError("{} return value requested. Currently supported are (pandas,dict,list, raw)")

            return toRet

        def link_sets_of_entities(self, associable_query_left, associable_quey_right, relationship_label,
                                   session_id=None, perc_entries_right=0.95, comparison_cutoff=0.9, pre_processing_function=None):
            """
                Performs probabilistic linking between TWO sets of entities based on values of specific fields.

                The ACT of establishing a link between two entities can be based on the values of two fields from the entities themselves OR from two other LINKED entities.

                To abstract this, the QueryLEFT and QueryRIGHT expressions MUST return a dataset that contains the value of the field to be associated / tested with that noted and the NODE to attach the link on.
                The NODE MUST be of CORE type (not the specialisation, because (for example) you don't know what sort of affiliation you are going to get)
                OBVIOUSLY, there has to be a 1:1 correspondence between that particular node and the field. This is very important

                Semantics:

                    Link LEFT **TO** RIGHT: LEFT->RIGHT
                        Means look for LEFT into RIGHT.
                        The RIGHT is assumed to be a long string that has to go through a PIPELINE
                            The PIPELINE INVOLVES:
                                Preprocessing (substitutions, etc) in the form of a callable
                                Tokenisation or SPLITTING. This can also be a callable

                        The LEFT is trimmed to some percentage of its length (percEntries)
                        The RIGHT can contain duplicates but to avoid multigraphs the RIGHT is SETIFIED

                Parameters:
                    percEntries             : Focuses the length distribution of the LEFT
                    comparison_cutoff        : The cut off of the soft comparison
                    pre_processing_function   : The function that is applied to the LEFT to pre-process it
                    tokenisationFunction    : The function that splits the long string of the RIGHT into tokens to send it to the comparison function
                    session_id               : An identifier that identifies the links that are established by this particular run


                Notes:
                    A link has two outcomes: Matched and non-Matched. There should be a way to return those entities that were not matched, although these can be discovered by a query later on.
            """
            if session_id is None:
                # If no session ID was provided, we have to give this session a unique identifier
                session_id = str(uuid.uuid4())
            k = 0

            # Constants required for the linking to run
            splitRule = re.compile("\s*(,|;|\.)\s*")

            # Run the queries to create two sets
            dictLEFT = self.cypher_query(associable_query_left, result_as="dict")
            dictRIGHT = self.cypher_query(associable_quey_right, result_as="dict")

            # To reduce the number of comparisons trim down the length of countries to the lengths of X% of the most common lengths.

            all_items_left = list(dictLEFT.keys())
            all_items_left_histogram = sorted(list(collections.Counter(list(map(lambda x: len(x), all_items_left))).items()), key=lambda x: x[1], reverse=True)

            # The sum of all terms of the histogram
            max_sum = sum(list(map(lambda x: x[1], all_items_left_histogram)))
            # Initialise the cumulative sum list to the length of the histogram and fill in the first term
            cumsum = [0] * len(all_items_left_histogram)
            cumsum[0] = all_items_left_histogram[0][1] / max_sum
            # Calculate the rest of the cumulative sum
            for m in range(1, len(all_items_left_histogram)):
                cumsum[m] = cumsum[m - 1] + all_items_left_histogram[m][1] / max_sum
            # Now pick as much as the user specified
            m = 0
            cumsum_len = len(cumsum) - 1
            while cumsum[m] <= perc_entries_right and m < cumsum_len:
                m += 1
            # Now trim the index
            trimmed_lengths = list(map(lambda x: x[0], all_items_left_histogram[:m]))
            trimmed_items_left = dict(list(filter(lambda x: len(x[0]) in trimmed_lengths, dictLEFT.items())))
            all_trimmed_items_left = list(trimmed_items_left.keys())

            # Set up a batch process to apply these links in batched mode
            batched_links = batchprocess.OGMTransactionBatch(batch_size=1024)

            # Main step of linking
            for an_item_right in dictRIGHT.items():
                if not (k % 1000):
                    rptr("Processed {} Items".format(k))
                    batched_links.apply()
                k += 1

                # Standardise entry
                # TODO: LOW, Can this be turned into some kind of map?
                # This function has some side effects. You work on those side-effects
                standardised_item_right = pre_processing_function(an_item_right[0]) if pre_processing_function else an_item_right[0]

                # Tokenise and retain anything within the determined country len for
                # the first stage as a set to remove duplicates
                item_right_tokens = splitRule.split(standardised_item_right)

                item_right_tokens_to_compare = set(filter(lambda x: len(x) in trimmed_lengths, item_right_tokens))

                # Now collect appearances of LEFT into the RIGHT
                for aKeyComponent in item_right_tokens_to_compare:
                    # This is the point of actual comparison
                    comparison_result = difflib.get_close_matches(aKeyComponent, all_trimmed_items_left, cutoff=comparison_cutoff)
                    if len(comparison_result) >= 1:
                        # OK, now we have matches and have to establish links.
                        # Here, we ignore the headings of the values of the index and simply link the contents
                        an_item_right_items = list(an_item_right[1].values())
                        an_item_left_items = list(trimmed_items_left[comparison_result[0]].values())
                        for aRIGHTItem in an_item_right_items:
                            for aLEFTItem in an_item_left_items:
                                # aRIGHTItem.associations.connect(aLEFTItem, {'process_id': session_id, 'rel_label': relationship_label})
                                # if isinstance(aRIGHTItem, coreModels.AssociableItem) and isinstance(aLEFTItem, coreModels.AssociableItem):
                                #     aRIGHTItem.associations.connect(aLEFTItem, {'process_id': session_id, 'rel_label': relationship_label})
                                batched_links.add_item(batchprocess.ItemRelationship(aRIGHTItem.associations, aLEFTItem,
                                                                                     {"process_id": session_id,
                                                                                      "rel_label": relationship_label}))
                    else:
                        # TODO: HIGH, Turn this error into an exception
                        # sys.stdout.write("{}:Can't match to country\n".format(an_affiliation.id))
                        pass

            batched_links.apply()

    instance = None

    def __init__(self, connection_uri=None, uname=None, pword=None, host="localhost", port=7687):
        if not CitehoundManager.instance:
            CitehoundManager.instance = CitehoundManager.__CitehoundManager(connection_uri=connection_uri,
                                                                      uname=uname,
                                                                      pword=pword,
                                                                      host=host,
                                                                      port=port)

    def __getattr__(self, item):
        return getattr(self.instance, item)


# Configure an CitehoundManager
grid_importer_record = {"name": "GRID",
                        "description": "Imports the GRID database (https://www.grid.ac/). Expects a JSON file.",
                        "object": datainput.GRIDDataItemBatchInsert()}

ror_importer_record = {"name": "ROR",
                        "description": "Imports the ROR database (https://ror.org/). Expects a JSON file.",
                        "object": datainput.RORDataItemBatchInsert()}


mesh_importer_record = {"name": "MESH",
                        "description": "Imports the MESH historical tree. Expects a JSON file",
                        "object": datainput.MeSHLongitudinalDataItemInsert()}

pubmed_importer_record = {"name": "PUBMED",
                          "description": "Imports academic journal abstracts from PUBMED. Expects an XML file.",
                          "object": datainput.PUBMEDDataItemInsert()}

pubmed_batch_importer_record = {"name": "PUBMED_BATCH",
                                "description": "Imports academic journal abstracts from PUBMED. Expects an XML file. "
                                               "(Batch importer)",
                                "object": datainput.PUBMEDDataItemBatchInsert()}

# Create the insight manager singleton object
CM = CitehoundManager()
# Register the importers
CM.register_importer(grid_importer_record)
CM.register_importer(ror_importer_record)
CM.register_importer(mesh_importer_record)
CM.register_importer(pubmed_importer_record)
CM.register_importer(pubmed_batch_importer_record)
