"""
Models that are specified by Pubmed's schema

:author: Athanasios Anastasiou
:date: Mar 2023

"""
import neomodel
from . import core


class AssociableMeSHTermSpecialisationRelationship(neomodel.StructuredRel):
    """
    A relationship from child to parent that bears a single attribute with the MeSH Tree Number that
    leads to a particular descriptor.
    """
    # The tree number by which a particular MeSH Term specialises its higher level
    tree_number = neomodel.StringProperty(required=True)
    # Year this tree number was first assigned to this DUI
    valid_from = neomodel.IntegerProperty(required=True)
    # Year this tree number was last assigned to this DUI (empty (null) if the connection is still valid)
    valid_to = neomodel.IntegerProperty()


class PubmedMeSHQualifierAssociation(neomodel.StructuredRel):
    """
    A relationship that represents the association of a qualifier with a particular MeSH term via an article
    """
    article_id = neomodel.StringProperty(required=True)
    major_topic = neomodel.BooleanProperty(required=True)


class PubmedMeSHTermAssociation(neomodel.StructuredRel):
    """
    Represents the association of a MeSH term with an article
    """
    major_topic = neomodel.BooleanProperty()


class PubmedMeSHQualifierSpecialisationRelationship(neomodel.StructuredRel):
    """
    The qualifier specialisation counter part of qualifiers that have their own hierarchy
    """
    # The tree number by which a particular MeSH qualifier specialises its higher level
    tree_number = neomodel.StringProperty(required=True)
    # Year this tree number was first assigned to this DUI
    valid_from = neomodel.IntegerProperty(required=True)
    # Year this tree number was last assigned to this DUI (empty (null) if the connection is still valid)
    valid_to = neomodel.IntegerProperty()


class PubmedMeSHTermAlias(neomodel.StructuredNode):
    """
    A simple alias for a given DUI.

    An alias is a DescriptorName that a given DUI might have been known as in the past. It therefore tracks
    "rename" operations on the same DUI.
    """
    alias = neomodel.StringProperty(required=True, index=True)


class PubmedMeSHTermAliasAssociation(neomodel.StructuredRel):
    valid_from = neomodel.IntegerProperty(required=True)
    valid_to = neomodel.IntegerProperty()


class PubmedMeSHTerm(core.AssociableItem):
    """
    A MeSH term that can be associated with an article.
    """

    # InsightQL can have a prepopulated database of MeSH terms or create new terms if they don't exist.
    # In the latter case, the minimal fields required to be available are the UI and the name of the descriptor
    # Unique Identifier for this MeSH Term
    dui = neomodel.StringProperty(unique_index=True)
    descriptor_name = neomodel.StringProperty(index=True)
    # Terms can be fully populated as a result of a MeSH import or not fully populated if they
    # were brought in to the database via an article import.
    fully_populated = neomodel.BooleanProperty(default=False, index=True)

    descriptor_class = neomodel.StringProperty(index=True)

    date_created = neomodel.DateProperty()
    date_established = neomodel.DateProperty()
    date_revised = neomodel.DateProperty()

    # Year this DUI first appeared in the descriptor files
    valid_from = neomodel.IntegerProperty(index=True)
    # Year this DUI was withdrawn
    valid_to = neomodel.IntegerProperty(index=True)

    aliases = neomodel.RelationshipTo("PubmedMeSHTermAlias",
                                      "PREVIOUSLY_KNOWN_AS",
                                      model=PubmedMeSHTermAliasAssociation)

    tree_number_list = neomodel.ArrayProperty(neomodel.StringProperty())

    # Relationship to other descriptors (tree). This edge bears the tree number fragment
    specialisation_of = neomodel.RelationshipTo("PubmedMeSHTerm",
                                                "SPECIALISATION_OF_TRM",
                                                model=AssociableMeSHTermSpecialisationRelationship)

    qualifiers_used = neomodel.RelationshipTo("PubmedMeSHTermQualifier",
                                              "QUALIFIED_BY",
                                              model=PubmedMeSHQualifierAssociation)

    scope_note = neomodel.StringProperty()


class PubmedMeSHTermQualifier(core.AssociableItem):
    """
    A qualifier that further specialises the use of a mesh term.

    Note: Qualifiers have their own tree structure.
    """
    qui = neomodel.StringProperty(unique_index=True)
    qualifier_name = neomodel.StringProperty(index=True, required=True)
    fully_populated = neomodel.BooleanProperty(default=False, index=True)
    valid_from = neomodel.IntegerProperty(index=True)
    valid_to = neomodel.IntegerProperty(index=True)
    specialisation_of = neomodel.RelationshipTo("PubmedMeSHTermQualifier",
                                                "SPECIALISATION_OF_QLF",
                                                model=PubmedMeSHQualifierSpecialisationRelationship)


class PubmedArticle(core.Article):
    """
    A pubmed Article.

    NOTE: At the moment, a PubmedArticle is pretty much the exact same thing as an Article because
    pubmed was the first database we used for large scale processing. However as it can be noted here,
    a pubmed article has a set of meshterms associated with it which is not expected for an Article
    in general.
    """
    mesh_terms = neomodel.RelationshipTo("citehound.models.pubmed.PubmedMeSHTerm", "HAS_MESHTERM", model=PubmedMeSHTermAssociation)


class PubmedAuthor(core.Author):
    """
    A Pubmed Author is simply defined by three elements of fore, middle and last name
    """
    fore_name = neomodel.StringProperty()
    initials = neomodel.StringProperty()
    last_name = neomodel.StringProperty()
    # The fullname is the concatenation of first,space,initials,space,last name
    full_name = neomodel.StringProperty(unique_index=True)


class PubmedAffiliation(core.Affiliation):
    """
    A Pubmed affiliation is a very simple string.
    """
    pass
