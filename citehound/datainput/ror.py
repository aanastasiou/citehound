"""
:author: Athanasios Anastasiou
:date: Mar 2023
"""

import sys
import os

from lxml import etree  # Handles XML
import json

import neo4j
import neomodel

import logging
import datetime

from .. import exceptions
from ..models import grid, pubmed
from .core import JSONDataItemReader, BaseDataItemBatchReaderMixin

from .. import batchprocess
import html

import copy
import gc


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
                                                   "name": x["geonames_city"]["city"]} if x["geonames_city"] not in (None, {}) else {"is_valid_geo_id": False, 
                                                                                                                     "geonames_id": "", "name": x["city"]}, 
                                        an_element["addresses"])),
                       "country": an_element["country"],
                       "geo_coordinates": list(map(lambda x: {"lat": x["lat"], "lng": x["lng"]}, an_element["addresses"])),
                       "types": an_element["types"],
                       # For more details around the reason for the filtering here, please see:
                       # https://github.com/ror-community/ror-updates/wiki/ROR-Metadata-Policies#relationships
                       "relationships": list(filter(lambda x:x["type"] in ("Parent", "Related"),an_element["relationships"]))})
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
        RORDataItemReader.__init__(self)
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
                                                                      "is_valid_geo_id": x["city"][0]["is_valid_geo_id"]} 
                                                                      if x["city"][0]["is_valid_geo_id"] else 
                                                                     {"name": x["city"][0]["name"],
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

        # except (neo4j.exceptions.ClientError, neomodel.exceptions.UniqueProperty) as ex:
        #     with open("thedump.json", "w") as fd:
        #         json.dump(a_batch, fd)
        #     print("ERROR!!!ERROR!!!ERROR!!!ERROR!!!ERROR!!!\n\n\n\n\n")
        #     sys.exit(-1)
        #     pass
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


