.. _citehound_installation:

============
Installation
============

This section details Citehound's installation process, from zero to a populated database that can be used for
further research over bibliographical datasets.

As a software package, Citehound requires the installation and configuration of certain components as well as
pre-requisite datasets to deliver its functionality.

Setting these pre-requisites up, *does not have to be repeated* for every bibliographical data research
project and can be simply "transferred across" when starting a new project.

This section covers the following points:

1. Citehound software installation & configuration
2. Pre-loading common datasets (e.g. MeSH, ROR)

At the end of this process a basic Citehound system (commonly referred to as ``project_base``) will have been setup
that can be used to "seed" other projects without having to carry out this lengthy process again.

Citehound software installation & configuration
================================================

This section of the installation is written primarily with * the Linux Operating System* in mind [#f1]_.

Pre-requisites
--------------

1. Start with a (basic Ubuntu Server, preferably) Linux image.

2. Make sure that the system has:

   * Python 3 

     * And at least `virtualenv <https://pypi.org/project/virtualenv/>`_.

   * `Graphviz <https://graphviz.org/>`_

   * The zip package.

   * A "container manager" (either Docker or Podman)

3. The Neo4J database server

   * You might already have a server instance available for this; or
   * Run the server using the Neo4j container image; or
   * Use *"Neo4J management"* software.


The absolutely essential resource here is the Neo4j database which can be managed in a 
number of different ways. 

Citehound contains some basic support for managing an underlying containerised Neo4j 
database and the rest of this section is written with that in mind. More information 
about managing a number of different servers using ``ineo`` can be found in the 
:ref:`Appendix <usingineo>`.


Installing Citehound
---------------------

1. Create a new directory and clone Citehound into it:

   ::

       > mkdir -p myprojects/bibresearch
       > cd myprojects/bibresearch
       > git clone https://github.com/aanastasiou/citehound.git

2. Create a virtual environment

   For example, using ``virtualenv``:

   ::

       > virtualenv -p python3.11 pyenv/
       > source pyenv/bin/activate

3. Install Citehound:

   ::

       > pip install -r requirements.txt
       > pip install ./

This concludes the installation of the basic software we are going to need in the next sections.

Configuration
-------------

1. Configure environment variables:

   ::

       > export NEO4J_USERNAME=neo4j
       > export NEO4J_PASSWORD=somepassword
       > export NEO4J_BOLT_URL="bolt://$NEO4J_USERNAME:$NEO4J_PASSWORD@localhost:7687"
       > export CITEHOUND_CONTAINER_BIN=`which podman`
       > export CITEHOUND_CONTAINER_IMG="docker.io/neo4j:4.4.18"
       > export CITEHOUND_DATA="/home/someuser/citehound_data/"

   .. warning::
       Please note the port that the BOLT URL is pointing at should match the one your Neo4j server is using, otherwise you will keep getting errors.

   These environment variables are as follows:

   * **NEO4J_USERNAME**: The username that is used to auhenticate with the database server
   * **NEO4J_PASSWORD**: The password that is used to auhenticate with the database server
   * **NEO4J_BOLT_URL**: The BOLT interface URL that is used to communicate with the database server
   * **CITEHOUND_CONTAINER_BIN**: The binary for the container manager (here `podman <https://podman.io/>`_).
   * **CITEHOUND_CONTAINER_IMG**: The "image" the database server will run from, this should match the database server you wish to use. For more information please see `here <https://neo4j.com/docs/operations-manual/current/docker/>`_.
   * **CITEHOUND_DATA**: An *existing directory* that will be used to host all Citehound projects in.


This concludes with the basic configuration of the Citehound package.

Creating ``project_base``
=========================

1. Create a Citehound project

   ::

     > cadmin.py db create project_base

   This step will create a sub-directory ``project_base`` within the directory you have 
   configured via the environment variable ``CITEHOUND_DATA``. This is where all data 
   for ``project_base`` are going to be held.

2. Activate the Citehound project

   ::

     > cadmin.py db start project_base

3. Initialise the Citehound database for ``project_base``

   This step initialises the *running* Neo4j server with a schema that enforces specific constraints that protect
   against common errors, accelerate queries via indexes and effectively performs de-duplication of data.

   ::

       > cadmin.py db init


This concludes with the basic configuration of the Citehound base project.


Loading common datasets
=======================

Prior to doing any meaningful work with Citehound, it is recommended to pre-load some datasets that
improve the precision and recall of queries against a given bibliographical dataset.

This is achieved largely by the ``cadmin.py`` program and the data flow is depicted in the following figure.

.. mermaid::

   graph LR;
       PB2[(Pubmed<br/>MeSH Terms)];
       GRID[(ror.org)];
       BibAdmin[cadmin.py];
       BibMESH[cmeshprep.py];
       BibDB[(Citehound)];

       GRID -- fetch ror --> BibAdmin;
       BibAdmin -- ingest data ROR ror_version.json --> BibDB;

       PB2 -- fetch mesh--> BibMESH;
       BibMESH --> BibAdmin;
       BibAdmin -- ingest data MESH MESH_master_tree.json --> BibDB;


Importing ROR
-------------

The `ROR <https://ror.org/>`_ dataset is a large database of research organisations around the world
and their "relationships". That is, for a given organisation, ROR describes its type (e.g. whether it is Governmental,
Educational, Private, etc), geographical location and other attributes but also if it is a department, campus of, part 
of a larger organisation and so on. The addition of the ROR dataset makes certain queries much easier and / or
accurate by exploiting knowledge about the organisations participating in the authorship of articles.

To understand why we need the ROR dataset, just consider that a given affiliation field in an academic journal entry
is a simple textual description of the organisation, possibly inter-dispersed with its postal address in no particular
order or format. In the worst case scenario, the affiliation contains all sorts of irrelevant information that have
managed to get past the quality assurance processes of the data provider.

Citehound uses ROR to disambiguate affiliations and enrich its queries. To continue with the previous example, with
ROR's availability it is now possible to query an organisation for all of its linked departments and then
ask Citehound to retrieve all papers that have originated from any of those. The same query without leveraging on the
hierarchy provided by ROR would involve a large number of conditionals over the free text field of the affiliation.

To import ROR to your ``project_base``:

1. Make sure that your ``project_base`` is active:

   * ``> podman container ls -a``

   If you cannot see your neo4j image up and running, then start it with:

   * ``cadmin.py db start project_base``

To achieve he same using ``ineo`` please see :ref:`here <ineo_basic_startup>`


2. Fetch the latest ROR dataset:

   * ``> cadmin.py fetch ror``
   * This downloads the latest release of ROR to the current working directory.

     - To send the file to a different directory, add the option ``--od``. For 
       more information please see :ref:`citehound_admin_doc`.

3. Unzip the downloaded archive

   * Suppose that step 2 led to the downloading of ``v1.20-2023-02-28-ror-data.zip``
   * ``> unzip v1.20-2023-02-28-ror-data.zip``
   * This results in a single JSON file (e.g. ``v1.20-2023-02-28-ror-data.json``)

4. Import it to Citehound:

   ::

       > cadmin.py ingest data ROR ./v1.20-2023-02-28-ror-data.json


This concludes with the importing of the ROR dataset. 

This step might take a while, depending on the spec of your network connection and 
database hardware but at the end, your database will contain the entirety of ROR.
That is a few thousand nodes and a few more thousand of relationships already.

For more details about the ROR database please see https://ror.org/


Importing MeSH
--------------

The Medical Subject Headings (MeSH) dataset is yet another significant hierarchy, 
especially when it comes to mining bibliographical data originating from Pubmed.

Citehound imports the **complete** MeSH database between the years 2002 and the 
present date.

If you need to understand why this is needed, then make sure that you read through the
:ref:`ref_importing_mesh_background` subsection, otherwise, feel free to jump directly
to subsection :ref:`ref_importing_the_mesh_hierarchy`.


.. _ref_importing_the_mesh_hierarchy:

Importing the complete MeSH hierarchy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Importing the complete MeSH Hierarchy to Citehound is done in two parts:

1. Download the primary XML data

   * These describe the MeSH hierarchy for every year since 2002.

2. Process the primary data files to produce a single JSON file

   * This file describes the MeSH tree, augmented with information about the lifetime and "trace" (within the tree) of every single code.

The typical workflow is as follows:

1. Make sure that your ``project_base`` is activated:

2. Fetch the MESH datasets

   * ``> cadmin.py fetch mesh``

     * This will download a set of XML files in the current working directory. These 
       datasets are fetched from a `pre-determined location <https://www.nlm.nih.gov/databases/download/mesh.html>`_.

3. Pre-process the XML datasets

   * ``> citehound_mesh.py preprocess -i ./ -o ./MESH_historical_tree.json``
     * Again, depending on the time span of the XML files you have downloaded, this step might take a few minutes to finish.
   * This step will produce the ``MESH_historical_tree.json`` file, in the current working directory
   * This file contains all the necessary information to describe **all the changes** that 
     have been applied to the MeSH hierarchy over the span of years and its size will be 
     at the order of magnitude of hundreds of Megabytes.
   * This is the single file that is required to import the MeSH hierarchy into Citehound.

3. Import the JSON file to Citehound

   ::

       > cadmin.py ingest data MESH ./MESH_historical_tree.json


This concludes with the data importing process.

It also means that you now have a solid ``project_base`` project that you can use to 
kickstart a given bibliographic research project.


Preserving and re-using ``project_base``
========================================

To avoid having to repeat this process to pre-load another database with the MeSH and ROR datasets it would be good to preserve ``project_base`` and keep it free from bibliographical data (i.e. actual publication data).

To create another database that is **BASED ON** ``project_base`` (i.e. is preloaded with 
ROR and MeSH):
::

  > cadmin.py db create my_project --based-on project_base

When you then come to activate ``my_project`` you will notice that it already contains 
the ROR and MeSH hierarchies pre-loaded.

If you are using ``ineo`` as your Neo4J DBMS manager, please see :ref:`here <ineo_preserve_and_reuse>`


Conclusion
==========

This concludes the process of creating the base project. The next step now is to import bibliographical data for a given analysis project.


-----

.. [#f1] Citehound was developed on Ubuntu 16.04 and revised under Ubuntu 22.04. Some prototyping of its functionality took place in the last few versions of Python 2 but the main system was developed on early versions of Python3. During the revisions of the code base circa Nov-Dec 2021, changes had to be applied to bring the system online. There is a certain satisfaction in turning the key years later and hearing the engine turning as if you stopped tinkering with it the previous day.

