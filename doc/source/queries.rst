====================
Working with queries
====================

Citehound provides the abiliy to store a number of queries along with your data.

These queries are in the form of Neo4j CYPHER queries and their purpose is to produce mainly 
tabular data that can readily be reviewed or visualised via other pieces of software.

This is very convenient when you find yourself running the same queries repeatedly to different 
collections of papers or periodically to the same search performed with different search parameters.

You do not need to know how to write Cypher queries. Citehound provides a comprehensive built-in list 
of such queries and the only thing you have to do is specify the "name" of the query and its parameters.

The rest of this section explores all the different capabilities exposed by the ``query`` sub-command and 
you can find out more about it by entering:

::

   > citehound_admin.py query --help


Some terminology
================

* Citehound maintains "Query Collections" along with the rest of the publication data.
* You can think of "Query Collections" as a set of "Key, Value" pairs, where the Key is a "Collection Name" and 
  the Value is a "Query Collection".
* A "Query collection" is itself a Key, Value pair, where the Key is the "Query Name" and the Value is the 
  Query itself.
* Queries are basically Neo4j Cypher queries.
* Citehound's built-in queries are accessible via the ``STD_QUERIES`` collection name. There is nothing 
  special about this collection, EXCEPT for the fact that if you do not specify the collection name in 
  some of the commands, it is assumed that you are targeting ``STD_QUERIES``.

In summary, to run a query you need to know its name and which collection it resides in.


Installing the ``STD_QUERIES`` collection
=========================================

Citehound comes with a list of queries that you can run from the command line, to obtain data 
that answer some elementary questions such as:

* What is the distribution of publications per: 

  - Year
  - Author
  - Institution

* Which publications were:

  - Submitted within a particular year
  - Written by a particular author
  - Attributed to a particular institution

And others. 

These queries are stored in the ``STD_QUERIES`` collection that 
contains quite a few queries to get you started.

To install these queries on a given database, all you have to do is:

::

   > citehound_admin.py query init

Browsing and exporting query collections
========================================

If everything has gone well, ``STD_QUERIES`` has been installed and is ready to execute queries on your database.

To confirm this, enter:

::

   > citehound_admin.py query ls

This should return somehing like:

::

   Collection, Number of queries
   STD_QUERIES, 11

This means that only ``STD_QUERIES`` has been installed and (at the time of writing this documentation) has 11 queries.

To see which queries are stored inside ``STD_QUERIES``, enter:

::

   > citehound_admin.py query ls -n STD_QUERIES

The parameter ``-n`` (or ``--collection-name``) specifies the query collection to list (``ls``).

This will produce (at the time of writing) something like:

::

  QueryName, Description
  LINK_DIAGNOSTIC, Returns total numbers of papers, authors, affiliations, affiliations linked to an institute, affiliations linked to a country.
  ARTICLES_OF_COUNTRY, Articles associated with a specific country. Articles must have been linked, see 'db link'. Expects parameter 'country_code'
  N_ARTICLES_PER_COUNTRY, Number of articles associated with a specific country
  ARTICLES_OF_INSTITUTE, Articles per institute. The linking operation must have run first, see 'db link'. Expects parameter 'institute_grid', see N_ARTICLES_PER_INSTITUTE on how to recover one
  N_AUTHORS_PER_INSTITUTE, Number of authors affiliated with their respective institutes
  N_ARTICLES_PER_INSTITUTE, Number of articles per institute. Articles must have been linked, see 'db link'
  N_AFFILIATIONS_PER_AUTHOR, Number of affiliations per author
  ARTICLES_OF_AUTHOR, List of articles attributed to a specific author. Must specify 'author_id'. See query N_ARTICLES_PER_AUTHOR query to recover a given 'author_id'
  N_ARTICLES_PER_AUTHOR, Number of articles per author
  ARTICLES_OF_YEAR, List of articles added to the dataset on the specific year. Must specify the 'year' parameter
  N_ARTICLES_PER_YEAR, Number of articles per year across the whole dataset

Exporting
---------

The default mode of listing the contents of a list produces a CSV output that only includes the Name and Description of a query stored wihin a collection but
does not really show the Cypher query that implements it.

To get a complete "dump" of everything, enter:

::

   > citehound_admin.py query ls -n STD_QUERIES --verbose

This will produce something like:

::

   ARTICLES_OF_AUTHOR:
     cypher: MATCH (a:Article)-[:AUTHORED_BY]->(u:Author) WHERE id(u)=$author_id RETURN
       a.article_id AS article_id, a.doi AS doi, a.title AS title, date(a.pub_date) AS
       pub_date ORDER BY pub_date DESC
     description: List of articles attributed to a specific author. Must specify 'author_id'.
       See query N_ARTICLES_PER_AUTHOR query to recover a given 'author_id'
   ...
   ...
   ...
   N_AUTHORS_PER_INSTITUTE:
     cypher: MATCH (i:Institute)<-[:ASSOCIATED_WITH{rel_label:'FROM_INSTITUTE'}]-(:Affiliation)<-[:AFFILIATED_WITH]-(u:Author)
       RETURN i.grid AS institute_id, i.name AS institute_name, count(u) AS n_affiliated_authors
       ORDER BY n_affiliated_authors DESC
     description: Number of authors affiliated with their respective institutes

You only see the first and last queries (at the time of writing) in this "dump" but it is enough to see that 
what you get is a YAML file with a self-explanatory format.


Using ``STD_QUERIES``
=====================

In general, to run queries in a collection you use:

::

   > citehound_admin.py query run

There are two types of ``run`` operations you can run, those 
that have parameters and those that do not.

Queries without parameters are the easiest, so, let's start with those.

Running simple queries without any parameter
--------------------------------------------

We are going to use the simplest standard query of *"What is the distribution of articles per year in my article collection?"*
to demonstrate how to run queries without parameters.

To do this enter:

::

   > citehound_admin.py query run N_ARTICLES_PER_YEAR

Notice here, no query collection was specified and the system assumes that you are referring to ``STD_QUERIES``. 
If the collection does not exist, you will receive a comprehensive message about it.

This might produce something like:

Running queries with parameters
-------------------------------

Suppose that you run the query in the previous section and now you are interested in extracting all the articles from the year 
with the most articles in your dataset.

This not only means running a query but modifying its parameters as well.

To do this, enter:

::

   > citehound_admin.py query run ARTICLES_OF_YEAR -p year=2020

.. note::

   * Query parameters without quotes are assumed to be numeric.
   * To enter a "string" parameter, you need to **enclose it in single quotes**.

This might produce something like:


Other administration operations
===============================

.. warning::

   Here be dragons.


.. note::

   Citehound takes some precaution to prevent the user from performing actions that 
   could lead to data loss.

   Although the program will ask you at least once to confirm potentially dangerous 
   operations (e.g. deletions), it will not stop you from carrying out an action.

   Both of these conditions are clearly noted in the following section.


Just as you created ``STD_QUERIES``, it is possible to create your own query collections





   

