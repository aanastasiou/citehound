.. _citehound_installation:

============
Installation
============

This section details the installation process of Citehound, from zero to a populated database that can be used for
further research over bibliographical datasets.

As a software package, Citehound requires the installation and configuration of certain components as well as
pre-requisite datasets. These pre-requisites, *do not have to be repeated* for every bibliographical data research
project and can be simply "transferred across" when starting a new project.

This section covers the following points:

1. Citehound software installation & configuration
2. Pre-loading common datasets

At the end of this process a basic Citehound system (commonly referred to as ``project_base``) will have been setup
that can be used to "seed" other projects without having to carry out this lengthy process again.

Citehound software installation & configuration
================================================

This section of the installation is written primarily with * the Linux Operating System* in mind [#]_.

Pre-requisites
--------------

1. Start with a (basic Ubuntu Server, preferably) Linux image.

2. Make sure that the system has:

    * Python 3 and at least `virtualenv <https://pypi.org/project/virtualenv/>`_.
    * `Graphviz <https://graphviz.org/>`_
    * The zip package.
    * Qt and PyQt libraries (`PyQt5 <https://pypi.org/project/PyQt5/>`_ at the time of writing).

3. Neo4J or a *"Neo4J management"* software.

   * Download and install `ineo <https://github.com/cohesivestack/ineo>`_

     * Citehound relies heavily on a graph database and requires at least 1 running Neo4J server.
     * You can install and manage one or more Neo4J servers locally or over the network (e.g. on a cloud
       computing provider)
     * However, we have found that certain tasks are made much easier by a Neo4J management software such as `ineo`
       and this is why it is recommended here.

Installing Citehound
---------------------

1. Create a new directory and clone Citehound into it:

   ::

       > mkdir -p myprojects/bibresearch
       > cd myprojects/bibresearch
       > git clone https://github.com/aanastasiou/citehound.git

2. Create a virtual environment

   ::

       > virtualenv -p python3.9 pyenv/
       > source pyenv/bin/activate

3. Install Citehound:

   ::

       > pip install -r requirements.txt
       > pip install ./

This concludes the installation of the basic software we are going to need in the next sections.

Configuration
-------------

1. Install a neo4j server using `ineo`:

   ::

       > ineo create -v 4.4.0 -d project_base

   This will download and configure a new instance based on neo4j (community edition) version 4.4.0.

   Take your time to review the installation because there are some key differences from a default community
   installation. To do this, go ahead and run:

   ::

       > ineo list

   which will most likely reply with something like:

   ::

       > instance 'project_base'
         VERSION: 4.4.0
         EDITION: community
         PATH:    /home/aanastasiou/.ineo/instances/project_base
         PORT:    7474
         HTTPS:   7475
         BOLT:    7476

   .. warning ::
       Please take note of the ports that each interface is running on. Especially the BOLT
       port, because it will be required when constructing the ``NEO4J_BOLT_URL`` in the next step.

2. Configure environment variables:

   ::

       > export NEO4J_USERNAME=neo4j
       > export NEO4J_PASSWORD=somepassword
       > export NEO4J_BOLT_URL="bolt://$NEO4J_USERNAME:$NEO4J_PASSWORD@localhost:7476"

   .. warning::
       Please note the port that the BOLT URL is pointing at, it is not a standard neo4j port and
       it has to match the one on your server, otherwise you will keep getting errors.

3. Initialise a Citehound database
   This step initialises the *running* Neo4j server with a schema that enforces specific constraints that protect
   against common errors, accelerate queries via indexes and effectively performs de-duplication of data.

   ::

       > cd citehound
       > citehound_admin.py db-init

This concludes with the basic configuration of the Citehound package.


Loading common datasets
=======================

Prior to doing any meaningful work with Citehound, it is recommended to pre-load some datasets that
improve the precision and recall of queries against a given bibliographical dataset.

This is achieved largely by the ``citehound_admin.py`` program and the data flow is depicted in the following figure.

.. mermaid::

   graph LR;
       PB2[(Pubmed<br/>MeSH Terms)];
       GRID[(grid.ac)];
       BibAdmin[citehound_admin.py];
       BibMESH[citehound_mesh_preprocess.py];
       BibDB[(Citehound)];

       GRID -- fetch_GRID.sh --> BibAdmin;
       BibAdmin -- import GRID --> BibDB;

       PB2-- fetch_MESH.sh --> BibMESH;
       BibMESH -- MESH_master_tree.json --> BibAdmin;
       BibAdmin -- import MESH --> BibDB;


Importing GRID
--------------

The Global Research Identifier Database (GRID) dataset is a large database of research organisations around the world
and their "relationships". That is, for a given organisation, GRID describes its type (e.g. is it Governmental,
Educational, private, etc), location and other attributes but also if it is a department, campus of, part of a larger
organisation and so on. In other words, GRID contains some hierarchy which can make certain queries much easier and / or
accurate.

To understand why we need the GRID dataset, just consider that a given affiliation field in an academic journal entry
is a simple textual description of the organisation, possibly inter-dispersed with its postal address in no particular
order or format. In the worst case scenario, the affiliation contains all sorts of irrelevant information that have
managed to get past the quality assurance processes of the data provider.

Citehound uses GRID to disambiguate affiliations and enrich its queries. To continue with the previous example, with
GRID's availability it is now possible to query an organisation for all of its linked departments and then
ask Citehound to retrieve all papers that have originated from any of those. The same query without leveraging on the
hierarchy provided by GRID would involve a large number of conditionals over the free text field of the affiliation.

To import GRID to your ``project_base``:

1. Make sure that your ``project_base`` is activated:

   * ``> ineo status project_base``
   * If it is not running, start it with ``> ineo start project_base``

2. Fetch the latest GRID dataset:

   * ``> data/fetch_GRID.sh``
   * This downloads the latest release of GRID into a ``data/GRID/`` directory.

3. Unzip the archive

   * ``> cd GRID``
   * ``> unzip GRID.zip``

     * The archive contains a number of files out of which the only one required to import
       the GRID database into Citehound is ``grid.json``.

4. Import it to Citehound:

   ::

       > citehound_admin import-data GRID GRID/grid.json


This concludes with the importing of the GRID dataset. This step will take a few minutes, depending on the spec of your
network connection and database hardware but at the end, your database will contain the entirety of GRID...That is a
few thousand nodes and a few more thousand of relationships already.

For more details about the GRID database please see https://grid.ac/



Importing MeSH
--------------

The Medical Subject Headings (MeSH) dataset is yet another significant hierarchy, especially when it comes to mining
bibliographical data originating from Pubmed.

Citehound however strives to import the **complete** MeSH database between the years 2002 and the present date.

If you need to understand why this is needed, then make sure that you read through the
:ref:`ref_importing_mesh_background` subsection, otherwise, feel free to jump directly
to subsection :ref:`ref_importing_the_mesh_hierarchy`.


.. _ref_importing_mesh_background:

Background to the MeSH hierarchy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Every Pubmed academic journal article entry has one or more subject descriptors associated with it, describing
the topic(s) that a given paper is dealing with. Here is an extract from an academic journal entry to show what these
descriptors look like:

.. literalinclude:: resources/code_examples/pubmed_sample_mesh.xml
       :language: xml

Each one of these descriptor "codes" (e.g. ``D000544``) points to a fully documented term in the MeSH hierarchy.

There is tremendous value in these descriptors because they are assigned by human beings and because
the descriptors themselves form a hierarchy. Here is what this hierarchy looks like from the MeSH browser:

.. _label_fig_mesh_peptides_example_opt:
.. figure:: resources/figures/fig_mesh_peptides_example_opt.png

       A branch of the MeSH tree showing the hierarchical organisation of the subject descriptors.

The motivation for including the ability to actively use these descriptors for querying data within Citehound is
the ability to form queries that can collect articles from "subject generalisations" by following the branches
of the MeSH tree to higher levels.

For example, given the "Aminoacids, Peptides and Proteins" branch of the MeSH tree depicted in
figure :numref:`label_fig_mesh_peptides_example_opt`, it is extremely straightforward to recall all papers that
have a particular descriptor attached to them. You just search for all articles that include the ``D016229`` descriptor.

But with the availability of the hierarchy, given a descriptor it is possible to retrieve the MeSH hierarchy "tree
location identifier", use that identifier to move up the hierarchy a level (to the more general subject), retrieve
the descriptors that describe the general subject and finally all of the papers that are in the same general subject as
a given paper.

Having access to the complete hierarchy might seem like an overkill, given that the tree identifier is self-describing.
That is, given ``D12.644.024``, it is already known that ``024`` is a specialisation of the ``644`` which is a
specialisation of the ``D12`` branch.

But, this is not the whole story. The same MeSH descriptor can belong to two branches of the MeSH tree but, more
importantly, the MeSH hierarchy is a *dynamic network*.

This changes everything.

Over time, new codes come into existence and older codes are withdrawn or, worse even, get merged or re-assigned. For
example, the term `Blockchain <https://meshb-prev.nlm.nih.gov/record/ui?ui=D000081186>`_ was only established in 2019
and if you try to search for ``D003293`` (also known as "Convulsions") in the 2021 version of the MeSH tree, you
`will not find that code <https://meshb-prev.nlm.nih.gov/search?searchInField=ui&searchType=exactMatch&searchMethod=SubString&q=D013135>`_.
And yet, ``D003293`` was being assigned to papers between the years of 2002 and 2004 when the tree was re-organised.

What this means is that if your search covers a long enough span (e.g. 3-5 years), your static search queries, simply
referencing a code, will be inaccurate.

How do we know?

In our research we came across this type of "problems" with codes very often, especially when trying to be very
specific (e.g. in rare diseases). It was already expected that a given query would return just a few results but
trying to expand this search with alternatives was now inhibited by the fact that the MeSH hierarchy was changing
throughout the time span that a given search was covering.

To counter-act this we needed to know how does the MeSH tree was changing over time. That is, which year a new code
was introduced, which year it was removed, which year it was modified (and how) and so on.

This is why the actual data importing process detailed further below, is split into two parts.


.. _ref_importing_the_mesh_hierarchy:

Importing the complete MeSH hierarchy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Importing the complete MeSH Hierarchy is a process that is split across two parts:

1. Download the primary XML data

   * These describe the MeSH hierarchy for every year since 2002.

2. Process the primary data files to produce a single JSON file

   * This file describes the MeSH tree, augmented with information about the lifetime and "trace" (within the tree)
     of every code.

The typical workflow is as follows:

1. Make sure that your ``project_base`` is activated:

   * ``> ineo status project_base``
   * If it is not running, start it with ``> ineo start project_base``

2. Fetch the MESH datasets

   * Run `> `data/fetch_MESH.sh``
   * This will download a set of XML files in ``data/MESH``. These datasets are fetched from pre-determined locations.

3. Pre-process the XML datasets

   * ``> citehound_mesh_preprocess -i data/MESH/ -o MESH_historical_tree.json``
   * Again, depending on the time span of the XML files you have downloaded, this step might take a few minutes to
     finish.
   * This step will produce the ``MESH_historical_tree,json`` file which is what will be imported to Citehound.
     The size of this file will be at the order of magnitude of hundreds of Megabytes.

3. Import the JSON file to Citehound

   ::

       > citehound_admin.py import-data MESH MESH_historical_tree.json


This concludes with the data importing process and it also means that you now have a solid ``project_base`` project
that you can use to kickstart a given bibliographic research project.

Archiving ``project_base``
==========================

To avoid having to repeat this process to pre-load another database with the MeSH and GRID datasets it would be good
to simply archive your whole ``project_base`` directory.

This can be found in ``~/.ineo/instances/project_base`` and it can be compressed with a simple:
``zip -r project_base.zip ~/.ineo/instances/project_base/*``.


Conclusion
==========

This concludes the process of creating the base project. The next step now is to import bibliographical data for a
given analysis project.



-----

.. [#] Citehound was developed on Ubuntu 16.04 and revised under Ubuntu 21.10. Some prototyping of its functionality
       took place in the last few versions of Python 2 but the main system was developed on early versions of Python3.
       During the revisions of the code base circa Nov-Dec 2021, very minor changes had to be applied to bring the
       system online. There is a certain satisfaction in turning the key years later and hearing the engine turning
       as if you stopped tinkering with it the previous day.
