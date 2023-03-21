# Provisional queries

This is a list of essential queries that should be provided along with the default system.

## Authors

### Nmber of articles per Author

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

### Return articles associated with a specific institute

```
MATCH (i:Institute)<-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-(:Affiliation)<-[:AFFILIATED_WITH]-(:Author)<-[:AUTHORED_BY]-(a:Article) WHERE i.grid="{INSTITITE_GRID}" RETURN distinct a.article_id, a.doi, a.title, date(a.pub_date) AS pub_date ORDER BY pub_date DESC
```

Where:

* `INSTITUTE_GRID` is the ID of the institute


# Country

### Number of articles per country

```
MATCH (a:Article)-[:AUTHORED_BY]->(u:Author)-[:AFFILIATED_WITH]->(f:Affiliation)-[:ASSOCIATED_WITH]-(c:Country) RETURN c.code AS country_code, c.name AS country_name, COUNT(a) AS articles_produced ORDER BY articles_produced DESC
```

### Return the articles produced within a specific country

```
MATCH (a:Article)-[:AUTHORED_BY]->(u:Author)-[:AFFILIATED_WITH]->(f:Affiliation)-[:ASSOCIATED_WITH]-(c:Country) WHERE c.code={COUNTRY_CODE} RETURN  a.article_id AS article_id, a.doi AS doi, a.title AS title, date(a.pub_date) AS pub_date ORDER BY pub_date DESC
```

Where:
* `COUNTRY_CODE` is a country's two letter code.

Notes:
* Articles are returned in reverse chronological order.



## Very basic figures describing the whole collection

* Total Number of papers
* Total Number of authors
* Total number of affiliations
* Total Number of affiliations linked to a City
* Total number fo affiliations linked to a country

```
match (a:Article) with count(a) as n_articles match (u:Author) with n_articles, count(u) as n_authors with n_articles, n_authors match (f:Affiliation) with n_articles, n_authors, count(f) as n_affiliations return n_articles, n_authors, n_affiliations
```


