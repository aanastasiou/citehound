====================
Working with plugins
====================

Citehound plugins provide a simple way to produce analytical results in different form, 
from the data held in Citehound.

Plugins are packaged and distributed as Python modules and can have their own dependencies 
that are entirely separate from the main Citehound project itself.

Once installed, plugins can be reviewed, return information about their functionality and 
parameters and finally be launched.

This section of the documentation will cover the *usage of plugins*.

A different section will be devoted on the details of developing plugins for Citehound.

Introduction
============

Plugins are Python programs that work together with Citehound and produce more complex
outputs than a CSV file typically produced by :ref:`queries <working_with_queries>`.

Citehound plugins are modules, in Python packages with the prefix ``citehound_plugin_``
in their name. For example, suppose a visualisation plugin that uses graphviz.org to visualise
an emerging citation network, based on your Citehound database. A possible name for this 
plugin could be ``author_network_graphviz``. In this case, the **package name** would be 
``citehound_plugin_author_network_graphviz`` but the **plugin name** would be 
``author_network_plugin``.

.. note::

   It is important to get this distinction right.

   To search for a plugin over pypi / git, you would use its complete **package name**, here 
   ``citehound_plugin_author_network_graphviz``. 

   Once the package is installed, the plugin is then addressed within Citehound with its 
   **plugin name** only.

   See for example, the section on listing the installed plugins further below.


All details that apply for the installation of Python packages, apply to installing
Citehound plugins as well. They can be installed via ``pip``, sourced from a git 
repository or pypi.org and can be uninstalled at will.

When a Citehound plugin launches, all operations within the plugin are "wrapped around" a 
transaction. Therefore, if the plugin crashes for any reason, data integrity is preserved. 
Only after the plugin has finished succesfully the set of operations described within the 
transaction is committed to the database. This of course applies to ``WRITE`` type of 
transactions that modify the database, raher than ``READ`` operations.

The entire plugin functionality is available through he Citehound adminstration script (``cadmin.py``)
under the command:

::

   > cadmin.py query ...


The rest of this section outlines each subcommand of ``query`` and its parameters with illustrative examples.


Listing installed plugins
=========================

To check if a plugin is installed, you can get a listing of the installed plugins with:

::

    > cadmin.py plugin ls


This will return a list of installed plugins under the heading ``Installed plugins``.

.. note::

   Plugins are listed here by their **plugin name**.


Inspecting installed plugins
============================

Citehound plugins aspire to be self-documenting. 

Plugins contain enough information to understand:

1. Their overall functionality
2. What their parameters are and what do they represent
3. What are valid values for those parameters.

Continuing from the above example, ``cadmin.py query ls`` returns a list of 
plugins and we would like to get more information about one of them, the one
called ``basic``.

All this information can be accessed via:

::

    > cadmin.py plugin info basic


This returns something like:

::


    Name: BasicPlugin
    
    
    Short Description:
    A simple plugin template for Citehound plugins.

    Long Description:
    This plugin contains the absolute minimal code for a user to start 
    developing and testing plugins.    
    
    Param.Name, Default value, Prompt, Description
    alpha, 0, Alpha coefficient:, The alpha coeff of the model
    mess, QUERY_COLLECTION, Query collection:, The collection to work on
    option_enabled, no, Enable this option?, Whether to enable the option or not


Launching plugins
=================

Having reviewed the installed plugins and reviewed the metadata of one (``basic``), we 
can now proceed to launch the plugin.

This is done with:

::

    > cadmin.py plugin launch basic

Most commonly, plugins will have mandatory parameters that **have to be set** before the plugin 
can proceed with its execution and optional parameters.

If no *mandatory* parameters are specified on the command line, Citehound will present a series of 
prompts to ensure that each mandatory plugin parameter is set to a valid value.

To set parameters at the command line, you can use:

::

    > cadmin.py plugin launch basic -p alpha=2

In fact, all parameters of a plugin can be set at the command line, in which case, Citehound will not 
present any interactive prompt to gather any unspecified plugin parameter.

This makes it easy to write scripts that call plugins sequentially to combine their outputs.
