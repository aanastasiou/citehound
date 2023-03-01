"""
A set of classes for dealing with batch CRUD operations on Neo4j via neomodel

:author: Athanasios Anastasiou
:date: Mar 2023
"""

import neomodel
import neo4j.exceptions
import asyncio
import datetime
import os

import pickle

# Abstract classes for transactions


class OGMTransaction:
    """
    Something that needs to take place within an OGM Transaction
    """
    def apply(self):
        """
        The point of actually running the transaction on the database.
        Anything that changes the state of the DBMS should execute in here.
        :return:
        """
        pass


class OGMTransactionBatch(OGMTransaction):
    """
    A batch of transactions that are supposed to be applied in one go to the database
    """
    def __init__(self, batch_size = 2048):
        self.batch_size = batch_size
        self._batch = []

    def add_item(self, an_item):
        self._batch.append(an_item)


    def extend_batch(self, another_batch):
        self._batch.extend(another_batch)

    def apply(self):
        """
        Applies the relationships in a batch mode on the database

        :return:
        """
        if len(self._batch)>0:
            chunk_indexes = list(range(0, len(self._batch), self.batch_size))
            batches = [self._batch[k:(k + self.batch_size)] for k in chunk_indexes[:-1]]
            batches.append(self._batch[chunk_indexes[-1]:])
            for a_batch in batches:
                neomodel.db.begin()
                for an_item in a_batch:
                    an_item.apply()
                neomodel.db.commit()
            self._batch = []


class OGMTransactionBatchAsync(OGMTransactionBatch):
    """
    Same as OGMTransactionBatch but uses Asyncio
    """

    def __init__(self, batch_size=2048):
        super().__init__(batch_size=batch_size)
        self.loop = asyncio.get_event_loop()

    async def _batch_apply(self,a_batch):
        neomodel.db.begin()
        for an_item in a_batch:
            an_item.apply()
        neomodel.db.commit()

    def apply(self):
        chunk_indexes = list(range(0, len(self._batch), self.batch_size))
        batches = [self._batch[k:(k + self.batch_size)] for k in chunk_indexes[:-1]]
        batches.append(self._batch[chunk_indexes[-1]:])

        return self.loop.run_until_complete(asyncio.gather(*[self._batch_apply(some_batch) for some_batch in batches]))



# Concrete classes for transactions
# TODO: MEDIUM, Relationships without data would lack a self._rel_data. But establishing it here would require an if on every "apply". So better split this into two classes
class ItemRelationship(OGMTransaction):
    """
    A very basic class that maintains a reference to two entities and the relationship that is supposed to be
    established between them
    """
    def __init__(self, left_relationship, right_entity, relationship_data=None):
        self._left_relationship = left_relationship
        self._right_entity = right_entity
        self._rel_data = relationship_data

    def apply(self):
        """
        Applies the relationship
        :return:
        """
        if self._rel_data is not None:
            self._left_relationship.connect(self._right_entity, self._rel_data)
        else:
            self._left_relationship.connect(self._right_entity)
