# Provisional queries

This is a list of essential queries that should be provided along with the default system.

## Number of papers per author

```
MATCH (a:Author)<-[r:AUTHORED_BY]-() RETURN a.full_name AS author_name, COUNT(r) AS n_articles_authored ORDER BY n_papers_authored DESC
```

## Number of papers per institute

```
MATCH (i:Institute)<-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-(:Affiliation)<-[:AFFILIATED_WITH]-(:Author)<-[:AUTHORED_BY]-(a:Article) return i.grid as institute_id, i.name as institute_name, count(a) as n_articles_produced ORDER BY n_articles_produced DESC
```

## Number of authors per institute

```
MATCH (i:Institute)<-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-(:Affiliation)<-[:AFFILIATED_WITH]-(u:Author) return i.grid as institute_id, i.name as institute_name, count(u) as n_affiliated_authors ORDER BY n_affiliated_authors DESC
```

## Number of distinct affiliations per author


## Number of articles per country



## Very basic figures describing the whole collection

* Total Number of papers
* Total Number of authors
* Total number of affiliations
* Total Number of affiliations linked to a City
* Total number fo affiliations linked to a country


