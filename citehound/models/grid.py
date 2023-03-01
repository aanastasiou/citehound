'''
The models that are associated with the importing of the GRID Database.
For more information please see https://www.grid.ac

:author: Athanasios Anastasiou
:date: Mar 2023
'''

import neomodel
from . import core
import random


class InstituteRelationship(neomodel.StructuredRel):
    """Abstracts the relationships field of the GRID schema"""
    relationship_type = neomodel.StringProperty()


class Institute(core.AssociableItem):
    """An institute defined as a subset of the schema used by GRID"""
    # GRID Content goes here
    grid = neomodel.StringProperty(required=True, unique_index=True)
    name = neomodel.StringProperty(required=True, index=True)
    lat = neomodel.FloatProperty(required = False, index=True)
    lng = neomodel.FloatProperty(required = False, index=True)
    city = neomodel.RelationshipTo('City', 'IN_CITY')
    institute_types = neomodel.RelationshipTo('citehound.models.grid.InstituteType', 'OF_INSTITUTE_TYPE')
    related_to = neomodel.RelationshipTo('Institute', 'RELATED_TO', model=InstituteRelationship)


# This is a general lambda to create a random string code up to length x composed of the characters in the string y
_genACode = lambda x, y: "".join([y[random.randint(0, len(y) - 1)] for aChar in range(0, x)])

# This is a parameter-less lambda with a specific call to genACode required for the default value of City.geonames_id field
_getACode = lambda: _genACode(8, 'ABCDEF0123456789_')


class City(core.AssociableItem):
    """A city as defined within GRID, which is referencing geoNames through an ID

    NOTE: The city information is not always available in GRID. But, every entry
    has to have a unique identification here. For this reason, there is a tag
    generation function available which guarantees that the city will get an ID
    even though such muiht not be available .
    """
    # This is the geonames ID towards the geonames database. It is normally an integer
    geonames_id = neomodel.StringProperty(unique_index=True, default=_getACode)
    # However, not all GRID entries have a geonames ID. In that case, the db index / constraint breaks.
    is_valid_geo_id = neomodel.BooleanProperty(default=True)
    # The name of the city
    name = neomodel.StringProperty(required=True, index=True)
    # The country it belongs to, again obtained directly from GRID
    country = neomodel.RelationshipTo('citehound.models.grid.Country', 'IN_COUNTRY')


class InstituteType(core.AssociableItem):
    """The type of institute as found in GRID"""
    type_label = neomodel.StringProperty(unique_index=True)


class Country(core.AssociableItem):
    """The country to which an institution is in.

    NOTE: At the moment, this must be an Associable too because through the affiliation it might be possible to associate
    a country but not its institution
    """
    code = neomodel.StringProperty(required=True, unique_index=True)
    name = neomodel.StringProperty(required=True, unique_index=True)
