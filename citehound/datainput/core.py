""" 
Base classes fo data readers and importers.

:author: Athanasios Anastasiou
:date: March 2023
"""

from lxml import etree  # Handles XML
import json


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

