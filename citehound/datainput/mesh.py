"""

:author: Athanasios Anastasou
:date: Mar 2023
"""
import os

import json

import neomodel

from ..models import pubmed
import datetime
from .core import XMLDataItemReader, JSONDataItemReader
from .. import batchprocess
import html

import copy
import gc


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
        mesh_nodes = pubmed.PubmedMeSHTerm.create_or_update(*list(map(lambda x:{"dui":x["DescriptorUI"] , "descriptor_name":x["DescriptorName"] , "fully_populated": True , "descriptor_class":x["DescriptorClass"] , "date_created":x["DateCreated"] , "date_established":x["DateEstablished"] , "date_revised":x["DateRevised"] , "valid_from":x["ValidFromTo"]["from"], "valid_to":x["ValidFromTo"]["to"], "tree_number_list":x["TreeNumberList"], "scope_note":x["ScopeNote"]}, self._current_master_tree.values())))
        # Flatten the aliases to be created in one go
        dui_to_alias = []
        for a_mesh_node in mesh_nodes:
            for an_alias in self._current_master_tree[a_mesh_node.dui]["Aliases"]:
                dui_to_alias.append({"dui": a_mesh_node.dui,
                                     "valid_from": an_alias[1]["from"],
                                     "valid_to": an_alias[1]["to"],
                                     "alias": an_alias[0]})
        # Now match mesh nodes to their alias strings
        mesh_node_aliases = list(zip(dui_to_alias, pubmed.PubmedMeSHTermAlias.create_or_update(*list(map(lambda x:{"alias":x["alias"]}, dui_to_alias)))))
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

