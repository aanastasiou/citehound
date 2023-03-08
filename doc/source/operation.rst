================================
Working with Citehound projects
================================

This section describes the typical process for loading a given bibliographical dataset into
Citehound before analysing it.

It is assumed here that you have already gone through the :ref:`citehound_installation` section that covers building
up the ``project_base`` "infrastructure" of datasets. Although a bibliographical dataset (a long list of data about
academic papers) can be loaded independently of ``project_base``, this would severely limit the possible querying
capabilities, especially in the case of mining Pubmed data.


Setting off to a new project
============================

So, the time has come to go through thousands of publications and somehow make sense of it all.

The most common research workflow involving Citehound proceeds as follows:

1. Work on solid literature search strategy
2. Run a thematic search on a literature database (e.g. Pubmed)
3. Download a bibliographical dataset in a supported format
4. Import the bibliographical dataset to Citehound
5. Link a given bibliographical dataset to external datasets
6. Proceed with further analysis

Hopefully, the first item in this list does not come as a surprise. Citehound was not built to substitute the part of
comprehending the information. You still need to make the effort of composing the picture that emerges from the
bibliography and how it fits in a given research context. What Citehound can help with is navigating through large
volumes of academic papers to summarise, or highlight, a particular aspect of the collection (e.g. *"How does research
on a given topic scale throughout the years given a bibliographical datset?"*). For more information around organising
a literature review, please
see `this guide <https://kib.ki.se/en/search-evaluate/systematic-reviews/structured-literature-reviews-guide-students>`_
or any other similar introduction to "Structured Literature Reviews".

The result of this search strategy is a set of rules (or "constraints") that define what constitutes an acceptable
paper for a given bibliographical dataset or not. This is a very important step in the whole analysis because
it becomes the semantic thread that binds together the concepts that are presented throughout the papers.

These first two steps already encode a large part of the success of a research project on bibliographical data (or,
that of a literature review).

Steps 3 onwards simply upload and link the data within Citehound and allow you to produce the evidence for answering
a question such as the one given above (*"How does research on a given topic scale throughout the years given a
bibliographical datset?"*).

.. mermaid::

       flowchart LR
              LDB[(Literature<br/>Databases)]
              DA[Data Analysis]
              Output[Results]
              subgraph BibSys [Citehound]
                     direction BT
                     BibDB1[(Citehound<br/>Project 1)]
                     BibDB2[(Citehound<br/>Project 2)]
                     BibDB3[(Citehound<br/>Project 3)]
                     BibDBN[(Citehound<br/>Project N)]
                     BibTools[Deduplication, <br/>Linkage, <br/> Querying]

                     BibTools<-->BibDB1
                     BibTools<-.->BibDB2
                     BibTools<-.->BibDB3
                     BibTools<-.->BibDBN

              end
              LDB --> BibSys
              BibSys <--> DA
              DA --> Output

The rest of this guide describes steps 3 onwards focusing on bibliographical data originating from Pubmed.


Creating a new Citehound project
=================================

Within Citehound, every different "literature review" or "bibliographical data research project" has its own underlying
database.

This is basically a Neo4J database, preloaded with the Citehound data model and a number of datasets.

This process is outlined in section :ref:`citehound_installation` and it results in ``project_base``.

If you are using ``ineo`` as your Neo4J manager, using ``project_base`` as the basis to a new project is as easy as
copying between two "instance" directories.

For example, to kickstart a ``pubmed_project_1`` from ``project_base``, all you have to do is:

1. Ensure that ``project_base`` is not running

   * ``> ineo stop project_base``

2. Drop to a terminal and copy ``project_base`` to ``pubmed_project_1``

   ::

        > cd ~/.ineo/instances
        > mkdir pubmed_project_1
        > cp -r project_base/ pubmed_project_1/

   * Now ``pubmed_project_1`` is pre-loaded with everything available in ``project_base``.


3. Start ``pubmed_project_1``

   * ``> ineo start pubmed_project_1``

This concludes with the creation of the ``pubmed_project_1`` and we are now ready to import a bibliographical dataset.


Importing a Pubmed bibliographical dataset to a project
=======================================================

.. _label_something:

.. mermaid::
    :caption: Importing Pubmed to Citehound

       graph LR;
              PB1[(Pubmed<br/>Articles)]
              PB3[pubmed.gov]
              PB2XL[pubmed2xl.com]
              BibAdmin[citehound_admin.py]
              BibDB[(Citehound)]

              PB1 --> PB3
              PB3 -- PMID:result_set.txt --> PB2XL
              PB2XL -- result_set.xml --> BibAdmin
              BibAdmin -- import PUBMED --> BibDB

Citehound was originally developed to process XML files exported from Pubmed.

The option to export a search "result set" as an XML file **used to** be available from Pubmed's search page but
not any more. Unfortunately, the currently available options to export data from the search page, result in datasets 
that are severely limited in terms of data processing.

Citehound includes a convenient tool that can download Pubmed data in XML format given a list of PMIDs.

Obtaining Pubmed XML data
-------------------------

To download a given set of publication data in XML format:

1. Run your query on pubmed.gov.
2. Export your result set in PMID format, suppose it is saved in ``pubmed_articles.pmid``.
3. To fetch the article data in XML format:
   
   * ``> citehound_admin.py fetch pubmedxml pubmed_articles.pmid > pubmed_articles.xml``

Now, given the ``pubmed_articles.xml`` Pubmed XML file, importing it to Citehound is achieved by:

1. Make sure that your ``pubmed_project_1`` is activated:

   * ``> ineo status pubmed_project_1``
   * If it is not running, start it with ``> ineo start pubmed_project_1``

2. Import the dataset

   * ``> citehound_admin.py ingest data PUBMED pubmed_articles.xml``


This concludes with importing a bibliographic dataset in Citehound.


Data linking
============

.. _label_operation_data_linking:

.. mermaid::
    :caption: Simplified diagram of the data linking process.

       graph RL
              BibAdmin[citehound_admin.py]
              BibDB[(Citehound)]

              BibAdmin -- db_problink --> BibDB
              BibDB --> BibAdmin


At this point, we have three different datasets in the system but without any connections between them. In order to link
the newly imported Pubmed bibliographical dataset with ROR, you need to run a "probabilistic linking" step.

This is achieved with:

::

    > citehound_admin.py db link

Very briefly, this script applies blocking on countries and then for each country runs a probabilistic linkage step
for the country's institutions.

For more information about the topic of "Record Linkage", `start here <https://en.wikipedia.org/wiki/Record_linkage>`_

Conclusion
==========

This concludes the process of importing and linking a Pubmed bibliographical dataset.

Onwards now, to detailed data processing examples.

-----

.. [#] So far, it has been possible to work with Pubmed, DBLP and ERIC without any problem. However, due to our
       specific interest, Citehound's Pubmed data processing capability has been more developed and is used here as a
       demonstrator.

.. [#] The Pubmed XML repository is like a document database where there is a massive catalogue indexed by the article's
       PMID. Pubmed XML files are simply collections of PMID indexed entries.

.. [#] Pubmed's XML database is a massive catalog of "article records", each one indexed by its PMID. The entire
       database is available from `this link <https://www.nlm.nih.gov/databases/download/pubmed_medline.html>`_. With
       these files it is possible to create a local indexable and searchable "pubmed engine"...with a little bit more
       effort of course.


