"""
Standard queries reviewed and supplied by citehound.

:author: Athanasios Anastasiou
:date: Mar 2023
"""
STD_QUERIES = {"N_ARTICLES_PER_YEAR":{"description": "Number of articles per year across the whole dataset",
                                      "cypher": "MATCH (a:Article) RETURN date(a.pub_date).year AS year, COUNT(a) AS n_articles ORDER BY year DESC"},
               "ARTICLES_OF_YEAR":{"description": "List of articles added to the dataset on the specific year. Must specify the 'year' parameter",
                                   "cypher": "MATCH (a:Article) WHERE date(a.pub_date).year=$year RETURN a.article_id AS article_id, a.doi AS doi, a.title AS title, date(a.pub_date) AS pub_date ORDER BY pub_date DESC"},
               "N_ARTICLES_PER_AUTHOR":{"description": "Number of articles per author",
                                        "cypher": "MATCH (a:Author)<-[r:AUTHORED_BY]-() RETURN id(a) AS author_id, a.full_name AS author_name, COUNT(r) AS n_articles_authored ORDER BY n_articles_authored DESC"},
               "ARTICLES_OF_AUTHOR":{"description": "List of articles attributed to a specific author. Must specify 'author_id'. See query N_ARTICLES_PER_AUTHOR query to recover a given 'author_id'",
                                     "cypher": "MATCH (a:Article)-[:AUTHORED_BY]->(u:Author) WHERE id(u)=$author_id RETURN a.article_id AS article_id, a.doi AS doi, a.title AS title, date(a.pub_date) AS pub_date ORDER BY pub_date DESC"},
               "N_AFFILIATIONS_PER_AUTHOR":{"description": "Number of affiliations per author",
                                            "cypher": "MATCH (a:Author)-[r:AFFILIATED_WITH]->(b:Affiliation) RETURN id(a) AS author_id, a.full_name AS full_name, count(b) AS affiliation_count ORDER BY cnt DESC"},
               "N_ARTICLES_PER_INSTITUTE":{"description": "Number of articles per institute. Articles must have been linked, see 'db link'",
                                           "cypher": "MATCH (i:Institute)<-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-(:Affiliation)<-[:AFFILIATED_WITH]-(:Author)<-[:AUTHORED_BY]-(a:Article) RETURN i.grid AS institute_id, i.name AS institute_name, COUNT(a) AS n_articles_produced ORDER BY n_articles_produced DESC"},
               "N_AUTHORS_PER_INSTITUTE":{"description": "Number of authors affiliated with their respective institutes",
                                          "cypher": "MATCH (i:Institute)<-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-(:Affiliation)<-[:AFFILIATED_WITH]-(u:Author) RETURN i.grid AS institute_id, i.name AS institute_name, count(u) AS n_affiliated_authors ORDER BY n_affiliated_authors DESC"},
               "ARTICLES_OF_INSTITUTE":{"description": "Articles per institute. The linking operation must have run first, see 'db link'. Expects parameter 'institute_grid', see N_ARTICLES_PER_INSTITUTE on how to recover one",
                                        "cypher": "MATCH (i:Institute)<-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-(:Affiliation)<-[:AFFILIATED_WITH]-(:Author)<-[:AUTHORED_BY]-(a:Article) WHERE i.grid=$institute_grid RETURN DISTINCT a.article_id AS article_id, a.doi AS doi, a.title AS title, date(a.pub_date) AS pub_date ORDER BY pub_date DESC"},
               "N_ARTICLES_PER_COUNTRY":{"description": "Number of articles associated with a specific country",
                                         "cypher": "MATCH (a:Article)-[:AUTHORED_BY]->(u:Author)-[:AFFILIATED_WITH]->(f:Affiliation)-[:ASSOCIATED_WITH]-(c:Country) RETURN c.code AS country_code, c.name AS country_name, COUNT(a) AS articles_produced ORDER BY articles_produced DESC"},
               "ARTICLES_OF_COUNTRY":{"description": "Articles associated with a specific country. Articles must have been linked, see 'db link'. Expects parameter 'country_code'",
                                      "cypher": "MATCH (a:Article)-[:AUTHORED_BY]->(u:Author)-[:AFFILIATED_WITH]->(f:Affiliation)-[:ASSOCIATED_WITH]-(c:Country) WHERE c.code=$country_code RETURN  a.article_id AS article_id, a.doi AS doi, a.title AS title, date(a.pub_date) AS pub_date ORDER BY pub_date DESC"},
               "LINK_DIAGNOSTIC":{"description": "Returns total numbers of papers, authors, affiliations, affiliations linked to an institute, affiliations linked to a country.",
                                  "cypher": "MATCH (a:Article) WITH COUNT(a) AS n_articles MATCH (u:Author) WITH n_articles, COUNT(u) AS n_authors MATCH (f:Affiliation) WITH n_articles, n_authors, COUNT(f) AS n_affiliations MATCH (:Affiliation)-[r:ASSOCIATED_WITH{rel_label:'FROM_COUNTRY'}]->() WITH n_articles, n_authors, n_affiliations, COUNT(r) AS n_affiliations_asc_to_country MATCH (:Affiliation)-[r:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]->() RETURN n_articles, n_authors, n_affiliations, n_affiliations_asc_to_country, COUNT(r) as n_affiliations_asc_to_institute"},
              }
