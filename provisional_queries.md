# Provisional queries

This is a list of essential queries that should be provided along with the default system.

## Articles

### Articles Per Year

```
MATCH (a:Article) RETURN COUNT(a) AS n_articles, date(a.pub_date).year AS year ORDER BY year DESC
```

### Articles of a specific year

```
MATCH (a:Article) WHERE date(a.pub_date).year={YEAR} RETURN a.article_id, a.doi, a.title, date(a.pub_date) as pub_date ORDER BY pub_date DESC
```

Where:

* `YEAR` is the specific year


## Authors

### Number of articles per Author

```
MATCH (a:Author)<-[r:AUTHORED_BY]-() RETURN id(a) as author_id, a.full_name AS author_name, COUNT(r) AS n_articles_authored ORDER BY n_articles_authored DESC
```

### Articles of a given author

```
MATCH (a:Article)-[:AUTHORED_BY]->(u:Author) WHERE id(u)={AUTHOR_ID} RETURN a.article_id, a.doi, a.title, date(a.pub_date) AS pub_date ORDER BY pub_date DESC
```

Where:

* `AUTHOR_ID` is obtained from the previous query and is a query parameter

### Distinct affiliations per author

```
MATCH (a:Author)-[r:AFFILIATED_WITH]->(b:Affiliation) return id(a) as author_id, a.full_name as full_name, count(b) as affiliation_count order by cnt desc
```


## Institutes

### Number of articles per institute

```
MATCH (i:Institute)<-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-(:Affiliation)<-[:AFFILIATED_WITH]-(:Author)<-[:AUTHORED_BY]-(a:Article) return i.grid as institute_id, i.name as institute_name, count(a) as n_articles_produced ORDER BY n_articles_produced DESC
```

### Number of authors per institute

```
MATCH (i:Institute)<-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-(:Affiliation)<-[:AFFILIATED_WITH]-(u:Author) return i.grid as institute_id, i.name as institute_name, count(u) as n_affiliated_authors ORDER BY n_affiliated_authors DESC
```

### Articles associated with a given institute

```
MATCH (i:Institute)<-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-(:Affiliation)<-[:AFFILIATED_WITH]-(:Author)<-[:AUTHORED_BY]-(a:Article) WHERE i.grid="{INSTITITE_GRID}" RETURN distinct a.article_id, a.doi, a.title, date(a.pub_date) AS pub_date ORDER BY pub_date DESC
```

Where:

* `INSTITUTE_GRID` is the ID of the institute


# Country

### Number of articles per country (where all affiliations are associated with that same country)

```
MATCH (a:Article)-[:AUTHORED_BY]->(u:Author)-[:AFFILIATED_WITH]->(f:Affiliation)-[:ASSOCIATED_WITH]-(c:Country) RETURN c.code AS country_code, c.name AS country_name, COUNT(a) AS articles_produced ORDER BY articles_produced DESC
```

### Articles from two or more countries.


### Articles associated ONLY with a specific country

```
MATCH (a:Article)-[:AUTHORED_BY]->(u:Author)-[:AFFILIATED_WITH]->(f:Affiliation)-[:ASSOCIATED_WITH]-(c:Country) WHERE c.code={COUNTRY_CODE} RETURN  a.article_id AS article_id, a.doi AS doi, a.title AS title, date(a.pub_date) AS pub_date ORDER BY pub_date DESC
```

Where:
* `COUNTRY_CODE` is a country's two letter code.

Notes:
* Articles are returned in reverse chronological order.

### Articles from authors in two or more countries



## Very basic figures describing the whole collection

* Total Number of papers
* Total Number of authors
* Total number of affiliations
* Total Number of affiliations linked to an institute
* Total number of affiliations linked to a country

```
MATCH (a:Article) 
      WITH COUNT(a) AS n_articles
           MATCH (u:Author) 
	         WITH n_articles, COUNT(u) AS n_authors
		      MATCH (f:Affiliation) 
			        WITH n_articles, n_authors, COUNT(f) AS n_affiliations
			         MATCH (:Affiliation)-[r:ASSOCIATED_WITH{rel_label:"FROM_COUNTRY"}]->()
				       WITH n_articles, n_authors, n_affiliations, COUNT(r) AS n_affiliations_asc_to_country
				            MATCH (:Affiliation)-[r:ASSOCIATED_WITH{rel_label:"FROM_INSTITUTE"}]->()
					          return n_articles, n_authors, n_affiliations, n_affiliations_asc_to_country, COUNT(r) as n_affiliations_asc_to_institute
```

### Affiliations to institute per year
```
MATCH (a:Article)-[:AUTHORED_BY]->(:Author)-[:AFFILIATED_WITH]->(:Affiliation)-[r:ASSOCIATED_WITH{rel_label:"FROM_INSTITUTE"}]->()
					          return COUNT(r) as n_affiliations_asc_to_institute, date(a.pub_date).year as year order by year desc
```

