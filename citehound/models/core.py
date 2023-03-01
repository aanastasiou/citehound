"""
The core backend models to access the graph database

:author: Athanasios Anastasiou
:date: Mar 2023
"""

import neomodel
import neoads


class AssociableRelationship(neomodel.StructuredRel):
    """The associable relationship captures the process by which this relationship was established as well as
    the date it was applied"""
    # An ID that identifies the process by which this relationship was established
    process_id = neomodel.StringProperty(required=True)
    # The date and time this association was established on
    established_on = neomodel.DateTimeProperty(default_now=True)
    # The label that characterises this relationship which is used to query it
    # TODO: MED, This works for unweighted, propertyless edges that denote a simple association. But to denote that this edge is part of a graph, we need more information associated with this edge. If the edge model cannot be extended, this field should be turned into a JSON field with a given format.
    rel_label = neomodel.StringProperty(required=True)


class AssociableItem(neoads.ElementDomain):
    """Base class for all associable bibliographical items in the database.

    This design choice was taken because it was impossible to predict
    in advance what sort of association needs might emerge.

    At the time of writing:
        An Article can be associated with Keywords, MeSH terms
        An Affiliation can be associated with Country and / or Institution

    And in the future it might that other entities of the schema will need to be tagged arbitrarily.

    NOTE: This ability is provided to TAG certain entities, NOT to abuse it with the establishment of arbitrary connections without any regard to data modeling principles.
    """
    # A reflexive relationship with other artifacts which an entity can be linked with. These can be specific thesaurus terms (having a specific ID and description for example) or just arbitrarily defined keywords
    associations = neomodel.RelationshipTo("citehound.models.core.AssociableItem", "ASSOCIATED_WITH", model=AssociableRelationship)


class Article(AssociableItem):
    """
    The base class that defines the minimum information expected to be found in any bibliographic database about an article
    """

    # A unique id that references the article
    article_id = neomodel.StringProperty(required=True, unique_index=True)
    # The title of the article
    title = neomodel.StringProperty(required=True, index=True)
    # The journal within which this article appears
    journal_iso = neomodel.StringProperty(required=True)
    # The publication date that this article appeared in the journal
    pub_date = neomodel.DateProperty(required=True)
    # The article DOI
    doi = neomodel.StringProperty(required=False, index=True)
    # The abstract of the article as it is lifted from the archive
    abstract = neomodel.StringProperty()
    # The list of authors
    author_list = neomodel.RelationshipTo("citehound.models.core.Author", "AUTHORED_BY")


class AffiliationRelationship(neomodel.StructuredRel):
    """
    An affiliation relationship is used to capture the affiliation of an author,
    AT THE TIME OF WRITING A PAPER."""
    article_id = neomodel.StringProperty(required=True)


class Author(AssociableItem):
    """
    The base class that defines the minimum information for an author

    NOTE: It is very difficult to define an accurate enough model for authors with the
    data that is readily available in the majority of databases today (i.e. a simple string
    identifying the author, without some ID of some sort (e.g. ORCID))
    """

    # The affiliation of the author
    # NOTE: Not all databases define affiliations (ERIC for example does not)
    affiliated_with = neomodel.RelationshipTo("citehound.models.core.Affiliation", "AFFILIATED_WITH", model=AffiliationRelationship)
    # TODO: MED, Add //PubmedArticle[MedlineCitation/Article/AuthorList/Author[Identifier[@Source="ORCID"]]


class Affiliation(AssociableItem):
    """
    The base class that defines the minimum information for affiliation.
    
    NOTE: It is very difficult to define a meaningful affiliation entity with the 
    information that is currently available in commonly used databases. Therefore 
    only a very general string is provided here to store the original affiliation string.
    This can be used later on as the basis to provide further associations
    """
    original_affiliation = neomodel.StringProperty(required=True, unique_index=True)
    # TODO: MED, Add //PubmedArticle[MedlineCitation/Article/AuthorList/Author[Identifier[@Source="ORCID"]]/AffiliationInfo/Identifier[@Source="GRID"]]
