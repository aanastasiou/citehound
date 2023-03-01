""" 
Data readers and importers.

:author: Athanasios Anastasiou
:date: March 2023
"""

import os

from lxml import etree  # Handles XML
import json

import neo4j
import neomodel

import logging

from .. import exceptions
from .models import grid
from .models import pubmed
import datetime

from . import batchprocess
import html

import copy
import gc


class BaseDataItemReader:
    """
    Abstract class that handles "itemised" reading of entities from an archive.
    """

    def on_begin_extract(self, an_archive):
        """
        Fired before the data item extraction starts from a particular archive
        """
        pass;

    def on_dataitem_extract(self, an_element):
        """
        Accepts a raw data item from the archive and returns a dictionary with the extracted information.

        Note: This function MUST return a value. This pattern, enables us to chain together various reader and build on
        their functionality
        """
        return an_element

    def on_end_extract(self):
        """
        Fired at the end of the data item extraction process. Can be used to return things to the process that called the reader.
        """
        return True

    def read_archive(self, an_archive):
        """
        Kickstarts the whole reading process from an archive

        :param an_archive: String, URI towards the archive.
        :return:
        """
        pass


class BaseDataItemBatchReaderMixin:
    """
    Adds batched functionality to data item readers.

    Note: Batched insertions to the database was an implicit requirement from the way the Neo4j driver works where, it is
    faster to do batch insertions that single transactions to the database.
    """
    def __init__(self, batch_size=1024):
        """
        Initialises a batch inserter with some batch_size.
        In addition to on_dataitem_extract, this class provides also an on_batch_ready function that is called every batch_size
        items.

        :param batch_size: Integer
        """
        self._batch_size = batch_size
        self._batch = []

    def on_dataitem_extract(self, an_element):
        """
        Effects the batching. an_element here is whatever element the underlying batched reader would have read.

        :param an_element: Dictionary, the structure is determined by the underlying item reader.
        :return:
        """
        data_element = super().on_dataitem_extract(an_element)
        if len(self._batch) < self._batch_size:
            self._batch.append(data_element)
        else:
            self.on_batch_ready(self._batch)
            self._batch=[data_element]

    def on_end_extract(self):
        """
        Submits the remaining batch of items for processing
        :return:
        """
        if len(self._batch)>0:
            self.on_batch_ready(self._batch)
            self._batch=[]

    def on_batch_ready(self, a_batch):
        """
        Called every batch_size items. Descending classes would put the dbms insertion code here
        :param a_batch:
        :return:
        """
        pass


class XMLDataItemReader(BaseDataItemReader):
    """
        Abstract class that prepares an XML reader for further element extraction.
    """

    def __init__(self, element_spec):
        """
        Initialises the XML data reader with the elementSpec, that is, the element that the XML parser
        responds to. For bibliographical data, this is the element that holds the article information
        """
        self._element_spec = element_spec

    def on_begin_extract(self, an_archive):
        """
        Constructs and returns a "context" object from the supplied archive
        :param an_archive:
        :return:
        """
        return etree.iterparse(an_archive, events=('end',), tag=self._element_spec)

    def on_dataitem_extract(self, an_element):
        """
        Accepts the XML data and returns a dictionary with the extracted information
        NOTE: If this function returns the dictionary then it can be used in cascaded form
        with a derived class that uses the extractor to send the data to different backends
        """
        return super().on_dataitem_extract(an_element)

    def read_archive(self, an_archive):
        """
        Sets up an XML parser and calls on_element_extract whenever that item is encountered
        """
        # For each tag....
        ctx = self.on_begin_extract(an_archive)
        for event, elem in ctx:
            # Do something with the article data
            self.on_dataitem_extract(elem)
            # Clean up and move on to the next item
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        return self.on_end_extract()


class JSONDataItemReader(BaseDataItemReader):
    """
    Abstract class that prepares a JSON reader for further data item extraction
    """

    def on_begin_extract(self, an_archive):
        """
        Reads the JSON file and returns a particular data field from which to import data.
        The default implementation returns the whole content of the JSON file

        :param an_archive:
        :return:
        """
        with open(an_archive, "r") as fd:
            data = json.load(fd)
        return data

    def on_dataitem_extract(self, an_element):
        """
        Accepts the JSON data and returns a dictionary with the extracted information
        :param an_element:
        :return:
        """
        return super().on_dataitem_extract(an_element)

    def read_archive(self, an_archive):
        """
        Sets up a JSON reader and calls on_element_extract whenever a particular item is encountered
        """
        data = self.on_begin_extract(an_archive)
        if type(data) is list:
            for a_data_item in data:
                self.on_dataitem_extract(a_data_item)
        else:
            for a_data_item in data.items():
                self.on_dataitem_extract(a_data_item)
        return self.on_end_extract()


# TODO: Medium, needs tests.
class MeSHDataItemReader(XMLDataItemReader):
    """
    Data reader for MeSH descriptors.

    Note: Contrary to Pubmed and GRID, this reader is not used directly to import a MeSH XML file to the database.
    Instead, it is used to read a given year's XML file and track the year-on-year changes and produce a JSON file
    which is THEN used to import the MeSH hierarchy in to the database
    """

    def __init__(self):
        super().__init__("DescriptorRecord")

    def on_dataitem_extract(self, an_element):
        """
        Extracts specific tags of interest from the "DescriptorRecord" of a MeSH term

        :param an_element: The etree DescriptorRecord element as retrieved from the archive
        :return: A dictionary with the information of interest.
        """

        # Extract specific tags from the mesh database
        # The bare essentials here are dui and descriptor_name
        ui = an_element.find("DescriptorUI").text
        descriptor_name = an_element.find("DescriptorName/String").text

        term_class = an_element.get("DescriptorClass")

        # Retrieve the dates created, established and revised
        date_created = None
        date_established = None
        date_revised = None

        dc = an_element.find("DateCreated")
        if dc is not None:
            date_created = datetime.date(year=int(dc.find("Year").text), month=int(dc.find("Month").text), day=int(dc.find("Day").text))

        de = an_element.find("DateEstablished")
        if de is not None:
            date_established = datetime.date(year=int(de.find("Year").text), month=int(de.find("Month").text), day=int(de.find("Day").text))

        dr = an_element.find("DateRevised")
        if dr is not None:
            date_revised = datetime.date(year=int(dr.find("Year").text), month=int(dr.find("Month").text), day=int(dr.find("Day").text))

        # Previous indexing and tree numbers
        previous_indexing = [an_indexing.text for an_indexing in an_element.findall("PreviousIndexingList/PreviousIndexing")]
        tree_numbers = [a_tree_number.text for a_tree_number in an_element.findall("TreeNumberList/TreeNumber")]

        # Allowable Qualifiers
        allowable_qualifiers_list = an_element.find("AllowableQualifiersList")

        allowable_qualifiers = None
        if allowable_qualifiers_list is not None:
            allowable_qualifiers = [{"QualifierUI": a_qualifier.find("QualifierUI").text,
                                     "QualifierName": a_qualifier.find("QualifierName/String").text} for a_qualifier in allowable_qualifiers_list.findall("AllowableQualifier/QualifierReferredTo")]
        # History Notes
        history_note_element = an_element.find("HistoryNote")
        history_note = html.unescape(history_note_element.text.lstrip().rstrip()) if not history_note_element is None else None

        # Concepts
        # Pickup the preferred scope note
        scope_note_element = an_element.find("ConceptList/Concept[@PreferredConceptYN='Y']/ScopeNote")
        scope_note = html.unescape(scope_note_element.text.lstrip().rstrip()) if not scope_note_element is None else None

        # Build the "item"
        term_item = {"DescriptorUI": ui,
                     "DescriptorName": descriptor_name,
                     "DescriptorClass": term_class,
                     "DateCreated": date_created,
                     "DateEstablished": date_established,
                     "DateRevised": date_revised,
                     "PreviousIndexingList": previous_indexing,
                     "TreeNumberList": tree_numbers,
                     "AllowableQualifiersList": allowable_qualifiers,
                     "HistoryNote": history_note,
                     "ScopeNote":scope_note}
        return term_item


class MeSHDataItemMemoryInsert(MeSHDataItemReader):
    """
    Ingests XML from a given MeSH data file and stores results in memory instead of the database
    """

    def __init__(self):
        super().__init__()

        # memory_storage is a dictionary that maps DUI to its data for fast lookups
        self.memory_storage = {}

    def on_dataitem_extract(self, an_element):
        data = super().on_dataitem_extract(an_element)
        self.memory_storage[data["DescriptorUI"]] = data
        return data


# TODO: Medium, Needs testing.
class MeSHLongitudinalDataItemReader(JSONDataItemReader):
    """
    Reads the intermediate JSON data file that stores a given MeSH hierarchy of codes

    Note: The MeSH hierarchy is dynamic. As a data structure it is composed by humans to be consumed by humans.
    There is no detailed set of machine readable diff changes to be able to track the tree longitudinally.
    This had to be created by manually tracking the XML files in time and noting the changes in specific fields (DUI,
    DescriptorName, TreeNumberList).

    As a result of this, the MeSH hierarchy (a dynamic temporal network) is not uploaded as a single XML file but
    through an intermediate JSON file. Why JSON? Because that was the easiest to store once all the XML files had
    been parsed.

    The reader expects a JSON file at its input. If it doesn't find it, it looks for an additional parameter that
    tells it where to look to find XML files to read from and construct the intermediate JSON file which it will store
    and then read to start the importing process
    """
    def __init__(self):
        super().__init__()

    def on_dataitem_extract(self, an_element):
        item_data = super().on_dataitem_extract(an_element)
        if item_data[1]["DateCreated"] is not None:
            item_data[1]["DateCreated"] = datetime.datetime.strptime(item_data[1]["DateCreated"], "%Y-%m-%d").date()
        if item_data[1]["DateEstablished"] is not None:
            item_data[1]["DateEstablished"] = datetime.datetime.strptime(item_data[1]["DateEstablished"], "%Y-%m-%d").date()
        if item_data[1]["DateRevised"] is not None:
            item_data[1]["DateRevised"] = datetime.datetime.strptime(item_data[1]["DateRevised"], "%Y-%m-%d").date()

        return item_data

    def read_archive(self, an_archive, xml_input_file_objects=None):
        """
        Reads an intermediate JSON archive and recreates the MeSH hierarchy within the database.

        :param an_archive: Path to the JSON data file. Part of this path will be re-used to store the JSON file at the end of the whole process.
        :param xml_input_file_objects: A list of two attribute objects (file, year), one for each file
        :return:
        """
        if not os.path.exists(an_archive):
            if xml_input_file_objects is not None:
                # The JSON file does not exist but we would like to create it.
                previous_year = {}
                current_master_tree = {}
                for a_file in enumerate(xml_input_file_objects):
                    # TODO, HIGH: Log this as an INFO
                    # print("Working on {}".format(a_file[1]["file"]))

                    U = MeSHDataItemMemoryInsert()
                    U.read_archive(a_file[1]["file"])

                    # Are there any added DUIs?
                    # DUIs that are in U but not in previous_year
                    added_duis = set(U.memory_storage.keys())-set(previous_year.keys())
                    for an_added_dui in added_duis:
                        current_master_tree[an_added_dui] = U.memory_storage[an_added_dui]
                        current_master_tree[an_added_dui]["ValidFromTo"] = {"from": a_file[1]["year"], "to":None}
                        current_master_tree[an_added_dui]["Aliases"] = [(current_master_tree[an_added_dui]["DescriptorName"], {"from": a_file[1]["year"], "to":None})]
                        current_master_tree[an_added_dui]["TreeNumberHistory"] = dict(list(map(lambda x:(x, [{"from": a_file[1]["year"], "to":None}]), current_master_tree[an_added_dui]["TreeNumberList"])))

                    # Are there any withdrawn DUIs?
                    # DUIs that are in previous_year but not in U
                    withdrawn_duis = set(previous_year.keys()) - set(U.memory_storage.keys())
                    for a_withdrawn_dui in withdrawn_duis:
                        current_master_tree[a_withdrawn_dui]["ValidFromTo"]["to"] = xml_input_file_objects[a_file[0]-1]["year"] # Note that you may not have sequential XML files for descriptors.

                    # All other DUIs will need to be monitored for year-on-year changes to specific elements
                    duis_to_update = set(U.memory_storage.keys()) - added_duis - withdrawn_duis
                    for a_dui in duis_to_update:
                        # NOTE DescriptorName CHANGES
                        if U.memory_storage[a_dui]["DescriptorName"]!=previous_year[a_dui]["DescriptorName"]:
                            current_master_tree[a_dui]["Aliases"][-1][1]["to"] = xml_input_file_objects[a_file[0]-1]["year"] # Note that you may not have sequential XML files for descriptors.
                            current_master_tree[a_dui]["Aliases"].append((U.memory_storage[a_dui]["DescriptorName"], {"from": a_file[1]["year"],"to": None}))
                        # NOTE TreeNumber CHANGES
                        # TreeNumbers are guaranteed to be unique. Therefore, although TreeNumberList is called a "list" it should really have been a Set.
                        if set(U.memory_storage[a_dui]["TreeNumberList"])!=set(previous_year[a_dui]["TreeNumberList"]):
                            # TreeNumbers Added
                            # They exist in the current year but not in the previous year
                            tree_numbers_added = set(U.memory_storage[a_dui]["TreeNumberList"]) - set(previous_year[a_dui]["TreeNumberList"])
                            # TreeNumbers Removed
                            tree_numbers_removed = set(previous_year[a_dui]["TreeNumberList"]) - set(U.memory_storage[a_dui]["TreeNumberList"])

                            # Add the new treenumbers
                            for a_treenumber_added in tree_numbers_added:
                                # If this tree number has not been assigned in the past, then assign it afresh
                                if not a_treenumber_added in current_master_tree[a_dui]["TreeNumberHistory"]:
                                    current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_added] = [{"from": a_file[1]["year"], "to": None}]
                                else:
                                    # If it has been assigned in the past, then add its historic record
                                    current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_added].append({"from": a_file[1]["year"], "to": None})

                            # Remove the removed treenumbers
                            for a_treenumber_removed in tree_numbers_removed:
                                # If there is just one historic record associated with this particular code then assign its end date
                                if len(current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_removed]) == 1:
                                    current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_removed][0]["to"] = xml_input_file_objects[a_file[0]-1]["year"] # Note that you may not have sequential XML files for descriptors.
                                else:
                                    # But, if there are more than one records associated with a code, it means that it has been re-branched in the past
                                    # and is now getting re-branched again under the same tree. This means that the latest record needs to be retrieved and ammended
                                    treenumber_historic_index = [index for index, historic_record in enumerate(current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_removed]) if historic_record["to"] is None]
                                    # TODO: If treenumber_historic_index is not just one for a given code, then this should be an error condition
                                    current_master_tree[a_dui]["TreeNumberHistory"][a_treenumber_removed][treenumber_historic_index[0]]["to"] = xml_input_file_objects[a_file[0]-1]["year"] # Note that you may not have sequential XML files for descriptors.

                        # Any other change
                        current_master_tree[a_dui].update(U.memory_storage[a_dui])

                    previous_year = copy.deepcopy(U.memory_storage)
                    # This saves memory
                    del(U)
                    gc.collect()
                # Process finished, save the master tree JSON file
                with open(an_archive, "w", encoding = "utf-8") as fd:
                    # TODO: LOW, This is a bit of a roundabout way of saving something that was a dictionary as a list only to immediatelly read it back and re-create the dictionary. Revise.
                    json.dump(list(current_master_tree.items()),fd, indent=4, sort_keys=True, default=str)
        # The file exists and the JSON reader simply starts the whole process
        return super().read_archive(an_archive)


class MeSHLongitudinalDataItemInsert(MeSHLongitudinalDataItemReader):
    """
    Reads the JSON intermediate MeSH term file and inserts in in the database taking care of updates.

    Note: This only updates the MeSH Hierarchy
    """

    def __init__(self):
        super().__init__()
        self._current_master_tree = {}
        self._master_lookup = {}

    def on_dataitem_extract(self, an_element):
        """
        Progressively creates the master_lookup tree and saves DUI data in memory prior to recreating the tree before inserting it to the database.
        :param an_element:
        :return:
        """
        item_data = super().on_dataitem_extract(an_element)
        self._current_master_tree[item_data[0]] = item_data[1]
        for a_treenumber in an_element[1]["TreeNumberHistory"]:
            if a_treenumber not in self._master_lookup:
                if not a_treenumber in self._master_lookup:
                    self._master_lookup[a_treenumber] = []
            for a_historic_record in an_element[1]["TreeNumberHistory"][a_treenumber]:
                self._master_lookup[a_treenumber].append((an_element[1]["DescriptorUI"], a_historic_record["from"], a_historic_record["to"]))
        return item_data

    def on_end_extract(self):
        """
        Once the JSON file has been loaded to memory, it is linked to a network (in memory). Then, all of its nodes update
        the nodes that are already in the database. The edges in the database are all erased and re-established from those
        in the network (which are supposed to be the most up to date).
        :return:
        """

        # This constant is required in date comparisons to substitute for "None"
        # occurences that denote events that are still current.
        max_year_const = datetime.datetime.now().year + 1

        batched_mesh_specialisation_edges = batchprocess.OGMTransactionBatch(batch_size=1024)
        batched_mesh_alias_edges = batchprocess.OGMTransactionBatch(batch_size=1024)

        # Do deletes first
        # Delete all alias nodes because they might be getting refreshed
        neomodel.db.cypher_query("MATCH (a:PubmedMeSHTermAlias) DETACH DELETE a")
        # Delete all specialisation_of relationships because they may be getting refreshed.
        neomodel.db.cypher_query("MATCH (:PubmedMeSHTerm)-[p:SPECIALISATION_OF]->(:PubmedMeSHTerm) DETACH DELETE p")

        # Recreate the hierarchy
        # Establish nodes
        mesh_nodes = models.pubmed.PubmedMeSHTerm.create_or_update(*list(map(lambda x:{"dui":x["DescriptorUI"] , "descriptor_name":x["DescriptorName"] , "fully_populated": True , "descriptor_class":x["DescriptorClass"] , "date_created":x["DateCreated"] , "date_established":x["DateEstablished"] , "date_revised":x["DateRevised"] , "valid_from":x["ValidFromTo"]["from"], "valid_to":x["ValidFromTo"]["to"], "tree_number_list":x["TreeNumberList"], "scope_note":x["ScopeNote"]}, self._current_master_tree.values())))
        # Flatten the aliases to be created in one go
        dui_to_alias = []
        for a_mesh_node in mesh_nodes:
            for an_alias in self._current_master_tree[a_mesh_node.dui]["Aliases"]:
                dui_to_alias.append({"dui": a_mesh_node.dui,
                                     "valid_from": an_alias[1]["from"],
                                     "valid_to": an_alias[1]["to"],
                                     "alias": an_alias[0]})
        # Now match mesh nodes to their alias strings
        mesh_node_aliases = list(zip(dui_to_alias, models.pubmed.PubmedMeSHTermAlias.create_or_update(*list(map(lambda x:{"alias":x["alias"]}, dui_to_alias)))))
        # Create yet another lookup from DUIs to database objects to be used for connections
        dui_to_dbnode = dict(zip(self._current_master_tree.keys(),mesh_nodes))
        # Establish fresh edges
        for a_mesh_node in mesh_nodes:
            # Connect the aliases
            aliases_to_connect = list(filter(lambda x:x[0]["dui"] == a_mesh_node.dui,mesh_node_aliases))
            for an_alias_to_connect in aliases_to_connect:
                batched_mesh_alias_edges.add_item(batchprocess.ItemRelationship(a_mesh_node.aliases,
                                                                                           an_alias_to_connect[1],
                                                                                           {"valid_from": an_alias_to_connect[0]["valid_from"],
                                                                                            "valid_to": an_alias_to_connect[0]["valid_to"]}))

            # Connect the tree edges
            for a_tree_number_edge in self._current_master_tree[a_mesh_node.dui]["TreeNumberHistory"].items():
                # Note: Oct-2018 If the specialisation has expired then the node must be connected to the hierarchy
                # as it was at the expiry date (so it needs an extra check on the dates)
                specialisation_of = ".".join(a_tree_number_edge[0].split(".")[:-1])
                if specialisation_of != "":
                    for temporal_data in a_tree_number_edge[1]:
                        # Filter the edges because they are not all valid for creation
                        node_to_connect = list(filter(lambda x: int(temporal_data["from"]) >= int(x[1]) and (int(temporal_data["to"] or max_year_const) <= int(x[2] or max_year_const)),
                                                      self._master_lookup[specialisation_of]))
                        for b_node in node_to_connect:
                            batched_mesh_specialisation_edges.add_item(batchprocess.ItemRelationship(a_mesh_node.specialisation_of,
                                                                                                                dui_to_dbnode[b_node[0]], {"tree_number": a_tree_number_edge[0],
                                                                                                                                           "valid_from": int(temporal_data["from"]),
                                                                                                                                           "valid_to": int(temporal_data["to"] or max_year_const)}))

        batched_mesh_specialisation_edges.apply()
        batched_mesh_alias_edges.apply()


class PUBMEDDataItemReader(XMLDataItemReader):
    """
        Specific code to import from PUBMED XML files as dicts
    """

    def __init__(self):
        """
        Basic initialisation of the object
        """
        # Initialise the mapper with the specific article tag
        super().__init__("PubmedArticle")
        # Setup local variables.
        self._mm2num = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9,
                        "Oct": 10, "Nov": 11, "Dec": 12}

    def _get_date(self, an_element):
        """
        Returns an article date as a proper datetime object. Also applies
        certain transformations if the month does not exist (defaults to 1),
        if the day does not exist (defaults to 1).
        """

        l_doc_date_year = an_element.findall("MedlineCitation/Article/Journal/JournalIssue/PubDate/Year")
        l_doc_date_month = an_element.findall("MedlineCitation/Article/Journal/JournalIssue/PubDate/Month")
        l_doc_date_day = an_element.findall("MedlineCitation/Article/Journal/JournalIssue/PubDate/Day")

        doc_date_year = int(l_doc_date_year[0].text) if len(l_doc_date_year) != 0 else None
        doc_date_month = (self._mm2num[l_doc_date_month[0].text] if not l_doc_date_month[0].text.isdigit() else int(
            l_doc_date_month[0].text)) if len(l_doc_date_month) != 0 else 1
        doc_date_day = int(l_doc_date_day[0].text) if len(l_doc_date_day) != 0 else 1

        return datetime.datetime(doc_date_year, doc_date_month, doc_date_day)

    def on_dataitem_extract(self, an_element):
        """
        Processes an article record from Pubmed xml
        """
        # TODO: HIGH, THIS QUERY NEEDS REVISION and to become parametrisable by the user
        # Apply criteria to accept or reject a record.
        if (not an_element.findall("MedlineCitation/Article/Journal/JournalIssue/PubDate/MedlineDate")) and (
                "Journal Article" in map(lambda x: x.text,
                                         an_element.findall("MedlineCitation/Article/PublicationTypeList/PublicationType"))):
            # EXTRACT SPECIFIC TAGS

            # PMID
            doc_identifier = an_element.find("PubmedData/ArticleIdList/ArticleId[@IdType='pubmed']").text

            # ArticleTitle
            l_doc_pub_title = an_element.findall("MedlineCitation/Article/ArticleTitle")
            doc_pub_title = "".join(map(lambda x: "".join(x.itertext()), l_doc_pub_title))

            if doc_pub_title is None:
                print("ERROR ERROR ERROR:{}".format(doc_identifier))

            # JournalTitle
            doc_journal_title = an_element.findall("MedlineCitation/Article/Journal/ISOAbbreviation")[0].text if len(
                an_element.findall("MedlineCitation/Article/Journal/ISOAbbreviation")) else ""
            # NOTE: Maybe keep the full text title too?
            # doc_journal_title = elem.findall("MedlineCitation/Article/Journal/Title")[0].text

            # PubDate
            pub_date = self._get_date(an_element)

            # doi
            doi = an_element.findall("PubmedData/ArticleIdList/ArticleId[@IdType='doi']")[0].text if len(an_element.findall("PubmedData/ArticleIdList/ArticleId[@IdType='doi']")) else ""

            # Authors
            l_doc_authors = an_element.findall("MedlineCitation/Article/AuthorList/Author")
            doc_authors = []
            for anAuthor in l_doc_authors:
                doc_authors.append(
                    {"LastName": anAuthor.findall("LastName")[0].text if anAuthor.findall("LastName") else "",
                     "Initials": anAuthor.findall("Initials")[0].text if anAuthor.findall("Initials") else "",
                     "ForeName": anAuthor.findall("ForeName")[0].text if anAuthor.findall("ForeName") else "",
                     # TODO: MEDIUM, Affiliations might be more than one (?)
                     "Affiliation": anAuthor.findall("AffiliationInfo/Affiliation")[0].text if anAuthor.findall(
                         "AffiliationInfo/Affiliation") else ""
                     })
            # DecriptorName
            l_mesh_terms = an_element.findall("MedlineCitation/MeshHeadingList/MeshHeading")
            doc_mesh_terms = []
            for aMeshTerm in l_mesh_terms:
                qualifiers_used = []
                for a_qualifier in aMeshTerm.findall("QualifierName"):
                    qualifiers_used.append({"MajorTopicYN": a_qualifier.get("MajorTopicYN"), "QUI": a_qualifier.get("UI"), "QualifierName": a_qualifier.text})
                descriptor_element = aMeshTerm.find("DescriptorName")
                doc_mesh_terms.append({"DescriptorName": descriptor_element.text, "UI": descriptor_element.get("UI"), "MajorTopicYN": descriptor_element.get("MajorTopicYN"), "Qualifiers":qualifiers_used})

                # Abstract
            l_doc_abstract = an_element.findall("MedlineCitation/Article/Abstract/AbstractText")
            doc_abstract = "".join(map(lambda x: "".join(x.itertext()), l_doc_abstract))

            # Build the 'document' and append it to the collection
            the_document = {"PMID": doc_identifier,
                           "ArticleTitle": doc_pub_title,
                           "ISOAbbreviation": doc_journal_title,
                           # NOTE: Retaining just the date here
                           "PubDate": pub_date.date(),
                           "Abstract": doc_abstract,
                           "AuthorList": doc_authors,
                           "MeshHeadingList": doc_mesh_terms,
                           "DOI": doi}
            return the_document


class GRIDDataItemReader(JSONDataItemReader):
    """
    Reads data items from GRID
    """

    def on_begin_extract(self, an_archive):
        """
        Extracts the "institutes" field from the grid.json file.
        :param an_archive: String, path to archive
        :return:
        """
        archive_data = super().on_begin_extract(an_archive)
        try:
            return archive_data["institutes"]
        except KeyError:
            raise exceptions.DataImportError("File does not contain 'institutes' section. Is it a GRID file? \n ({})".format(an_archive))

    def on_dataitem_extract(self, an_element):
        """
        Extracts specific fields from the JSON GRID file and prepares them for insertion in the database
        :param an_element:
        :return:
        """
        # Obsolete or redirected records do not have any further information
        record = {"status": an_element["status"],
                  "grid": an_element["id"]
                  }

        if an_element["status"] == "redirected":
            record.update({"redirect": an_element["redirect"]})

        if an_element["status"] == "active":
            record.update({"status": an_element["status"],
                           "grid": an_element["id"],
                           "name": an_element["name"],
                           "city": list(map(lambda x: {"is_valid_geo_id": True, "geonames_id": x["geonames_city"]["id"], "name": x["city"]} if x["geonames_city"] is not None else {"is_valid_geo_id": False, "geonames_id": "", "name": x["city"]}, an_element["addresses"])),
                           "country": list(map(lambda x: {"code": x["country_code"], "name": x["country"]}, an_element["addresses"])),
                           "geo_coordinates": list(map(lambda x: {"lat": x["lat"], "lng": x["lng"]}, an_element["addresses"])),
                           "types": an_element["types"],
                           "relationships": an_element["relationships"]})
        return record


class GRIDDataItemBatchInsert(BaseDataItemBatchReaderMixin, GRIDDataItemReader):
    """
    Batch insertion of GRID entities. This class takes the intermediate (dictionary) representation and
    executes the required inserts to the DBMS, through insight's models.

    Note: Please keep in mind the order by which inheritance is presented to this class.
    """
    def __init__(self, batch_size=1024):
        """
        Initialises this batch inserter taking into account the batch_size.

        Note: This is straightforward for a JSON reader but might require different initialisation options for other readers
        :param batch_size: Integer, the batch size at which transactions to the database will be taking place
        """
        BaseDataItemBatchReaderMixin.__init__(self, batch_size)
        GRIDDataItemReader.__init__(self)
        self._institute_relationships =  []

    def on_batch_ready(self, a_batch):
        """
        Inserts any extracted data in the intermediate (dictionary) format, to the database.

        Note: This is hapenning in batches in a single transaction for improved speed.
        :param a_batch:
        :return:
        """
        # TODO: MEDIUM, Need to make sure that obsolete and redirected entries are handled appropriately.
        active_institutes = list(filter(lambda x:x["status"] == "active", a_batch))
        # TODO: LOW, Need to remove this extra try, catch which deals with this issue https://github.com/neo4j-contrib/neomodel/issues/303
        logging.info("Writing GRID batch to database")
        try:
            with neomodel.db.transaction:
                # Create entities
                institutes = grid.Institute.get_or_create(*list(map(lambda x: {"grid": x["grid"], "name": x["name"], "lat": x["geo_coordinates"][0]["lat"], "lng": x["geo_coordinates"][0]["lng"]}, active_institutes)))
                cities = grid.City.get_or_create(*list(map(lambda x: {"geonames_id": x["city"][0]["geonames_id"], "name": x["city"][0]["name"], "is_valid_geo_id": x["city"][0]["is_valid_geo_id"]} if x["city"][0]["is_valid_geo_id"] else {"name": x["city"][0]["name"], "is_valid_geo_id": x["city"][0]["is_valid_geo_id"]}, active_institutes)))
                countries = grid.Country.get_or_create(*list(map(lambda x:{"code": x["country"][0]["code"], "name": x["country"][0]["name"]}, active_institutes)))
                institute_types = list(map(lambda x:grid.InstituteType.get_or_create(*list(map(lambda y: {"type_label": y}, x["types"]))), active_institutes))
                # Connect entities
                for an_institute in enumerate(institutes):
                    # Connect the institute to its city
                    an_institute[1].city.connect(cities[an_institute[0]])
                    # Connect the city to its country if it is not connected already
                    if countries[an_institute[0]] not in cities[an_institute[0]].country:
                        cities[an_institute[0]].country.connect(countries[an_institute[0]])
                    # Connect the institute types to the institute
                    for aType in institute_types[an_institute[0]]:
                        an_institute[1].institute_types.connect(aType)
        except neo4j.exceptions.ClientError as ex:
            pass
        # Save the relationships to be established AFTER all nodes have been saved
        self._institute_relationships.extend(list(map(lambda x: {"grid": x["grid"], "relationships": x["relationships"]}, active_institutes)))

    def on_end_extract(self):
        """
        Finalises the import process of the GRID dataset by establishing the connections between the relationships
        :return:
        """
        # THIS MUST BE DONE, otherwise the last batch doesn't get written to the DB!!!
        logging.info("Writing last GRID batch")
        super().on_end_extract()
        k = 0
        # TODO: LOW, Need to remove this extra try, catch which deals with this issue https://github.com/neo4j-contrib/neomodel/issues/303
        try:
            with neomodel.db.transaction:
                for anItem in self._institute_relationships:
                    if not (k % 1000):
                        logging.info("Inserted {}".format(k) if k > 0 else "Begin")
                    k += 1
                    theInstFrom = grid.Institute.nodes.get(grid=anItem["grid"])
                    for aRelationship in anItem["relationships"]:
                        theInstTo = grid.Institute.nodes.get(grid=aRelationship["id"])
                        rType = aRelationship["type"]
                        theInstFrom.related_to.connect(theInstTo, {"relationship_type": rType})
        except neo4j.exceptions.ClientError:
            pass
        logging.info("Done inserting GRID entities")


class RORDataItemReader(JSONDataItemReader):
    """
    Reads data items from ROR (https://ror.org/)

    ROR is a continuation of GRID (https://www.grid.ac/) and this code is very simillar to the
    GRID import process.
    """

    def on_begin_extract(self, an_archive):
        """
        Extracts the "institutes" field from the grid.json file.


        :param an_archive: String, path to archive
        :return:
        """
        # For more information on the data stucture see https://ror.readme.io/docs/ror-data-structure

        archive_data = super().on_begin_extract(an_archive)
        if type(archive_data) is not list and ["id", "name", "email_address", "types", "links", "aliases", "country"] not in archive_data:
            raise exceptions.DataImportError(f"File does not contain expected attributes. Is it a ROR release? \n ({an_archive})")
        return archive_data

    def on_dataitem_extract(self, an_element):
        """
        Extracts specific fields from the JSON GRID file and prepares them for insertion in the database
        :param an_element:
        :return:
        """
        # Obsolete or redirected records do not have any further information
        record = {"status": an_element["status"],
                  "grid": an_element["id"]
                  }

        record.update({"status": an_element["status"],
                       "grid": an_element["id"],
                       "name": an_element["name"],
                       "city": list(map(lambda x: {"is_valid_geo_id": True, 
                                                   "geonames_id": x["geonames_city"]["id"], 
                                                   "name": x["city"]} if x["geonames_city"] not in (None, {}) else {"is_valid_geo_id": False, 
                                                                                                                     "geonames_id": "", "name": x["city"]}, 
                                        an_element["addresses"])),
                       "country": an_element["country"],
                       "geo_coordinates": list(map(lambda x: {"lat": x["lat"], "lng": x["lng"]}, an_element["addresses"])),
                       "types": an_element["types"],
                       "relationships": an_element["relationships"]})
        return record


class RORDataItemBatchInsert(BaseDataItemBatchReaderMixin, RORDataItemReader):
    """
    Batch insertion of GRID entities. This class takes the intermediate (dictionary) representation and
    executes the required inserts to the DBMS, through insight's models.

    Note: Please keep in mind the order by which inheritance is presented to this class.
    """
    def __init__(self, batch_size=1024):
        """
        Initialises this batch inserter taking into account the batch_size.

        Note: This is straightforward for a JSON reader but might require different initialisation options for other readers
        :param batch_size: Integer, the batch size at which transactions to the database will be taking place
        """
        BaseDataItemBatchReaderMixin.__init__(self, batch_size)
        GRIDDataItemReader.__init__(self)
        self._institute_relationships =  []

    def on_batch_ready(self, a_batch):
        """
        Inserts any extracted data in the intermediate (dictionary) format, to the database.

        Note: This is hapenning in batches in a single transaction for improved speed.
        :param a_batch:
        :return:
        """
        # TODO: MEDIUM, Need to make sure that obsolete and redirected entries are handled appropriately.
        active_institutes = list(filter(lambda x:x["status"] == "active", a_batch))
        # TODO: LOW, Need to remove this extra try, catch which deals with this issue https://github.com/neo4j-contrib/neomodel/issues/303
        logging.info("Writing GRID batch to database")
        try:
            with neomodel.db.transaction:
                # Create entities
                institutes = grid.Institute.get_or_create(*list(map(lambda x: {"grid": x["grid"], "name": x["name"], "lat": x["geo_coordinates"][0]["lat"], "lng": x["geo_coordinates"][0]["lng"]}, active_institutes)))
                cities = grid.City.get_or_create(*list(map(lambda x: {"geonames_id": x["city"][0]["geonames_id"], 
                                                                      "name": x["city"][0]["name"], 
                                                                      "is_valid_geo_id": x["city"][0]["is_valid_geo_id"]} if x["city"][0]["is_valid_geo_id"] else {"name": x["city"][0]["name"], 
                                                                      "is_valid_geo_id": x["city"][0]["is_valid_geo_id"]}, 
                                                           active_institutes)))

                countries = grid.Country.get_or_create(*list(map(lambda x:{"code": x["country"]["country_code"], 
                                                                           "name": x["country"]["country_name"]}, 
                                                                 active_institutes)))

                institute_types = list(map(lambda x:grid.InstituteType.get_or_create(*list(map(lambda y: {"type_label": y}, 
                                                                                               x["types"]))), 
                                           active_institutes))
                # Connect entities
                for an_institute in enumerate(institutes):
                    # Connect the institute to its city
                    an_institute[1].city.connect(cities[an_institute[0]])
                    # Connect the city to its country if it is not connected already
                    if countries[an_institute[0]] not in cities[an_institute[0]].country:
                        cities[an_institute[0]].country.connect(countries[an_institute[0]])
                    # Connect the institute types to the institute
                    for aType in institute_types[an_institute[0]]:
                        an_institute[1].institute_types.connect(aType)
        except neo4j.exceptions.ClientError as ex:
            pass
        # Save the relationships to be established AFTER all nodes have been saved
        self._institute_relationships.extend(list(map(lambda x: {"grid": x["grid"], 
                                                                 "relationships": x["relationships"]}, 
                                                      active_institutes)))

    def on_end_extract(self):
        """
        Finalises the import process of the GRID dataset by establishing the connections between the relationships
        :return:
        """
        # THIS MUST BE DONE, otherwise the last batch doesn't get written to the DB!!!
        logging.info("Writing last GRID batch")
        super().on_end_extract()
        k = 0
        # TODO: LOW, Need to remove this extra try, catch which deals with this issue https://github.com/neo4j-contrib/neomodel/issues/303
        try:
            with neomodel.db.transaction:
                for anItem in self._institute_relationships:
                    if not (k % 1000):
                        logging.info(f"Inserted {k}" if k > 0 else "Begin")
                    k += 1
                    theInstFrom = grid.Institute.nodes.get(grid=anItem["grid"])
                    for aRelationship in anItem["relationships"]:
                        theInstTo = grid.Institute.nodes.get(grid=aRelationship["id"])
                        rType = aRelationship["type"]
                        theInstFrom.related_to.connect(theInstTo, {"relationship_type": rType})
        except neo4j.exceptions.ClientError:
            pass
        logging.info("Done inserting GRID entities")


class PUBMEDDataItemInsert(PUBMEDDataItemReader):
    """
    Implements an PUBMED article-by-article inserter to the database.

    Note: At this point in time, articles are inserted one at a time to be able to flag duplicates. If it later becomes
    possible to filter only those articles that do not already exist in the database, it might be possible to do batch
    inserts, in exactly the same way that we do batch inserts for GRID.
    """
    def on_dataitem_extract(self, an_element):
        article_data = super().on_dataitem_extract(an_element)

        if not article_data is None:

            # TODO: Low, Revise this for any better alternatives
            # Check if any affiliations might end up being longer than 4095 characters which is the longest
            # supported by Neo4j at the moment.
            for an_author in article_data["AuthorList"]:
                encoded_affiliation = bytearray(an_author["Affiliation"], "utf-8")
                if len(encoded_affiliation)>4000:
                    i = 4000;
                    while i>0 and not ((encoded_affiliation[i] & 0xC0) != 0x80):
                        i = i-1
                    an_author["Affiliation"] = encoded_affiliation[:i].decode("utf-8")

            if not article_data['ArticleTitle'] is None:
                # When inserting data from different datasets, it might be that a specific article already exists in the db.
                # In this case, if left unchecked, the PMID index will fail.
                try:
                    # Create the article. If the article exists in the database it will raise the UniqueProperty exception
                    the_article = models.pubmed.PubmedArticle(article_id=article_data['PMID'],
                                                              title=article_data['ArticleTitle'],
                                                              journal_iso=article_data['ISOAbbreviation'],
                                                              pub_date=article_data['PubDate'],
                                                              abstract=article_data['Abstract'],
                                                              doi=article_data["DOI"]).save()

                    # TODO: LOW, Remove this double try once the problems with neomodel are fixed
                    try:
                        with neomodel.db.transaction:
                            # Get or create the MeSH terms
                            the_term = models.pubmed.PubmedMeSHTerm.get_or_create(*list(map(lambda x: {"dui": x["UI"], "descriptor_name": x["DescriptorName"]}, article_data["MeshHeadingList"])))
                            # Get or create the MeSH term qualifiers
                            # The following creates a list of lists with one entry per MeSH Term
                            the_qualifiers = list(map(lambda x:models.pubmed.PubmedMeSHTermQualifier.get_or_create(*list(map(lambda u:{"qui":u["QUI"], "qualifier_name":u["QualifierName"]}, x["Qualifiers"]))), article_data["MeshHeadingList"]))
                            # Get or create the authors
                            the_author = models.pubmed.PubmedAuthor.get_or_create(*list(map(lambda x:{"fore_name": x["ForeName"], "initials": x["Initials"], "last_name": x["LastName"], "full_name": "{} {} {}".format(x["ForeName"], x["Initials"], x["LastName"])}, article_data["AuthorList"])))
                            # Get or create affiliations
                            # TODO: HIGH, Remove the exterior list from the interior x["Affiliation"] once the code has been updated
                            the_affiliation = list(map(lambda x:models.pubmed.PubmedAffiliation.get_or_create(*list(map(lambda y:{"original_affiliation":y}, [x["Affiliation"]]))), article_data["AuthorList"]))

                            # Create connections
                            # Connect the mesh terms
                            for a_meshterm in enumerate(the_term):
                                the_article.mesh_terms.connect(a_meshterm[1], {"major_topic":(article_data["MeshHeadingList"][a_meshterm[0]]["MajorTopicYN"] == "Y")})
                                # Connect the qualifiers
                                for a_qualifier in enumerate(the_qualifiers[a_meshterm[0]]):
                                    a_meshterm[1].qualifiers_used.connect(a_qualifier[1], {"major_topic": article_data["MeshHeadingList"][a_meshterm[0]]["Qualifiers"][a_qualifier[0]]["MajorTopicYN"]=="Y", "article_id": the_article.article_id})

                            # Connect the authors
                            for anAuthor in enumerate(the_author):
                                # Each author must be connected to their respective affiliation(s)
                                for anAffiliation in the_affiliation[anAuthor[0]]:
                                    if not anAffiliation.original_affiliation == "":
                                        anAuthor[1].affiliated_with.connect(anAffiliation, {"article_id": the_article.article_id})
                                the_article.author_list.connect(anAuthor[1])

                    except neo4j.exceptions.ClientError:
                        pass

                except neomodel.UniqueProperty:
                    # The article exists
                    pass


class PUBMEDDataItemBatchInsert(BaseDataItemBatchReaderMixin, PUBMEDDataItemReader):

    def __init__(self, batch_size=1024):
        """

        :param batch_size:
        """
        BaseDataItemBatchReaderMixin.__init__(self, batch_size)
        PUBMEDDataItemReader.__init__(self)

    def on_batch_ready(self, a_batch):
        """
        Inserts a batch of articles in the database.

        NOTE: The batch inserter does not check for duplicates.
        :param a_batch:
        :return:
        """
        # TODO: HIGH, The XML reader can have an internal "skip" step to be moving automatically to the next item if an item does not satisfy an internal criterion as it happens with the pubmed filters here.
        # This filtering is required because articles that do not match the entry filter return None (!)
        a_batch = list(filter(lambda x: type(x) is dict, a_batch))

        try:
            with neomodel.db.transaction:
                # Create the articles
                articles = models.pubmed.PubmedArticle.get_or_create(*list(map(lambda x: {"article_id": x["PMID"], "title": x["ArticleTitle"], "journal_iso":x["ISOAbbreviation"], "pub_date": x["PubDate"], "abstract": x["Abstract"], "doi": x["DOI"]}, a_batch)))
                # Create the MeSH terms
                article_mesh_terms = list(map(lambda x:models.pubmed.PubmedMeSHTerm.get_or_create(*list(map(lambda y: {"dui": y["UI"], "descriptor_name": y["DescriptorName"]}, x["MeshHeadingList"]))), a_batch))
                # Create the Qualifiers
                article_mesh_terms_qualifiers = list(map(lambda x: list(map(lambda y:models.pubmed.PubmedMeSHTermQualifier.get_or_create(*list(map(lambda z: {"qui": z["QUI"], "qualifier_name": z["QualifierName"]}, y["Qualifiers"]))), x["MeshHeadingList"])), a_batch))
                # Create the Authors
                article_authors = list(map(lambda x: models.pubmed.PubmedAuthor.get_or_create(*list(map(lambda y: {"fore_name": y["ForeName"], "initials": y["Initials"], "last_name": y["LastName"], "full_name": "{} {} {}".format(y["ForeName"], y["Initials"], y["LastName"])}, x["AuthorList"]))), a_batch))
                # Create the Author's Affiliations
                article_authors_affiliations = list(map(lambda x:list(map(lambda y: models.pubmed.PubmedAffiliation.get_or_create(*list(map(lambda z: {"original_affiliation":z}, [y["Affiliation"]]))), x["AuthorList"])), a_batch))
                # Connect the newly created entities
                for an_article in enumerate(articles):

                    for an_author in enumerate(article_authors[an_article[0]]):
                        for an_affiliation in enumerate(article_authors_affiliations[an_article[0]][an_author[0]]):
                            if not an_affiliation[1].original_affiliation == "":
                                an_author[1].affiliated_with.connect(an_affiliation[1], {"article_id": an_article[1].article_id})
                        an_article[1].author_list.connect(an_author[1])

                    for an_article_mesh_term in enumerate(article_mesh_terms[an_article[0]]):
                        for an_article_mesh_terms_qualifier in enumerate(article_mesh_terms_qualifiers[an_article[0]][an_article_mesh_term[0]]):
                            an_article_mesh_term[1].qualifiers_used.connect(an_article_mesh_terms_qualifier[1], {"article_id": an_article[1].article_id, "major_topic": a_batch[an_article[0]]["MeshHeadingList"][an_article_mesh_term[0]]["Qualifiers"][an_article_mesh_terms_qualifier[0]]["MajorTopicYN"] == "Y"})
                        an_article[1].mesh_terms.connect(an_article_mesh_term[1], {"major_topic": a_batch[an_article[0]]["MeshHeadingList"][an_article_mesh_term[0]]["MajorTopicYN"] == "Y"})

        except neo4j.exceptions.ClientError:
            pass
