"""
:author: Athanasios Anastasiou
:date: Mar 2023
"""
import neo4j
import neomodel

from .. import exceptions
from ..models import pubmed
from .core import XMLDataItemReader, BaseDataItemBatchReaderMixin
import datetime

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

            # TODO: HIGH, Send this to the logging stream
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
                    the_article = pubmed.PubmedArticle(article_id=article_data['PMID'],
                                                       title=article_data['ArticleTitle'],
                                                       journal_iso=article_data['ISOAbbreviation'],
                                                       pub_date=article_data['PubDate'],
                                                       abstract=article_data['Abstract'],
                                                       doi=article_data["DOI"]).save()

                    # TODO: LOW, Remove this double try once the problems with neomodel are fixed
                    try:
                        with neomodel.db.transaction:
                            # Get or create the MeSH terms
                            the_term = pubmed.PubmedMeSHTerm.get_or_create(*list(map(lambda x: {"dui": x["UI"], 
                                                                                                "descriptor_name": x["DescriptorName"]}, 
                                                                                      article_data["MeshHeadingList"])))
                            # Get or create the MeSH term qualifiers
                            # The following creates a list of lists with one entry per MeSH Term
                            the_qualifiers = list(map(lambda x:pubmed.PubmedMeSHTermQualifier.get_or_create(*list(map(lambda u:{"qui":u["QUI"], 
                                                                                                                                "qualifier_name":u["QualifierName"]}, 
                                                                                                                      x["Qualifiers"]))), article_data["MeshHeadingList"]))
                            # Get or create the authors
                            the_author = pubmed.PubmedAuthor.get_or_create(*list(map(lambda x:{"fore_name": x["ForeName"], 
                                                                                               "initials": x["Initials"], 
                                                                                               "last_name": x["LastName"], 
                                                                                               "full_name": f"{x['ForeName']} {x['Initials']} {x['LastName']}"}, 
                                                                                      article_data["AuthorList"])))
                            # Get or create affiliations
                            # TODO: HIGH, Remove the exterior list from the interior x["Affiliation"] once the code has been updated
                            the_affiliation = list(map(lambda x:pubmed.PubmedAffiliation.get_or_create(*list(map(lambda y:{"original_affiliation":y}, 
                                                                                                                 [x["Affiliation"]]))), 
                                                       article_data["AuthorList"]))

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
                articles = pubmed.PubmedArticle.get_or_create(*list(map(lambda x: {"article_id": x["PMID"], 
                                                                                   "title": x["ArticleTitle"], 
                                                                                   "journal_iso":x["ISOAbbreviation"], 
                                                                                   "pub_date": x["PubDate"], 
                                                                                   "abstract": x["Abstract"], 
                                                                                   "doi": x["DOI"]}, 
                                                                        a_batch)))
                # Create the MeSH terms
                article_mesh_terms = list(map(lambda x:pubmed.PubmedMeSHTerm.get_or_create(*list(map(lambda y: {"dui": y["UI"], 
                                                                                                                "descriptor_name": y["DescriptorName"]}, 
                                                                                                     x["MeshHeadingList"]))), 
                                              a_batch))
                # Create the Qualifiers
                article_mesh_terms_qualifiers = list(map(lambda x: list(map(lambda y:pubmed.PubmedMeSHTermQualifier.get_or_create(*list(map(lambda z: {"qui": z["QUI"], 
                                                                                                                                                       "qualifier_name": z["QualifierName"]}, 
                                                                                                                                            y["Qualifiers"]))), 
                                                                                      x["MeshHeadingList"])), 
                                                         a_batch))
                # Create the Authors
                article_authors = list(map(lambda x: pubmed.PubmedAuthor.get_or_create(*list(map(lambda y: {"fore_name": y["ForeName"], 
                                                                                                            "initials": y["Initials"], 
                                                                                                            "last_name": y["LastName"], 
                                                                                                            "full_name": f"{y['ForeName']} {y['Initials']} {y['LastName']}"}, 
                                                                                                 x["AuthorList"]))), 
                                           a_batch))
                # Create the Author's Affiliations
                article_authors_affiliations = list(map(lambda x:list(map(lambda y: pubmed.PubmedAffiliation.get_or_create(*list(map(lambda z: {"original_affiliation":z}, 
                                                                                                                                     [y["Affiliation"]]))), 
                                                                          x["AuthorList"])), 
                                                        a_batch))
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
