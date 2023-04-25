========
Appendix
========
 
.. _usingineo:

Using ``ineo`` as Neo4j Management Software
===========================================

Install ``ineo``
----------------

* Download and install `ineo <https://github.com/cohesivestack/ineo>`_

     * Citehound relies heavily on a graph database and requires at least 1 running Neo4J server.
     * You can install and manage one or more Neo4J servers locally or over the network (e.g. on a cloud
       computing provider)
     * However, we have found that certain tasks are made much easier by a Neo4J management software such as `ineo`
       and this is why it is recommended here.


Configuration
-------------

* Creating ``project_base`` using ``ineo``:

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
         PATH:    /home/someuser/.ineo/instances/project_base
         PORT:    7474
         HTTPS:   7475
         BOLT:    7476

   .. warning ::
       Please take note of the ports that each interface is running on. Especially the BOLT
       port, because it will be required when onfiguring the ``NEO4J_BOLT_URL`` in the next step.

.. _ineo_basic_startup:
   
Checking that a Citehound project is active
-------------------------------------------

* ``> ineo status project_base``

If this replies that ``project_base`` is inactive, then start it with:

* ``> ineo start project_base``


.. _ineo_preserve_and_reuse:

Preserving and re-using ``project_base``
----------------------------------------

If you have been following up this process using ``ineo``, then 
``project_base`` is located in ``~/.ineo/instances/project_base`` and it can 
be compressed with a simple: ``> zip -r project_base.zip ~/.ineo/instances/project_base/*``.

Using ``project_base`` as the basis for a new project is as easy as
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


