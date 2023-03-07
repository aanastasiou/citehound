Working With the MeSH hierarchy
===============================

Rationale
---------
The MeSH hierarchy is a complex data structure to represent and query. However importing 
and linking it with the rest of the datasets is a very important part of Citehound.

In brief, because of full detailed knowledge of the MeSH hieararchy, Citehound can 
embed a set of codes in a common lineage / history and automatically summarise 
publications in the different thematic subjects of the MeSH hierarhcy.

Introduction
------------
MeSH is a *...hierarchically-organised terminology for indexing and cataloging 
of biomedical information such as MEDLINE/PUBmed and other NLM databases"*. For 
more information please see `here <https://www.nlm.nih.gov/mesh/>`_

MeSH has been in existence since 1966, first in paper form, later in electronic 
format (XML) and since 2002 regularly updated and the files published via FTP.

MeSH is a hierarchical terminology oganised in a forest of 16 trees. Although 
it is *described* as a Tree, it actually looks more like a graph due to the fact 
that leafs can belong to more than one branches. For a given Tree, each *descriptor* 
composing its hierarchy has a unique **DescriptorUI** and a number of other data 
items associated with it. For a complete listing of the data associated with each 
descriptor, please see [here](https://www.nlm.nih.gov/mesh/xml_data_elements.html).

Extracted Data Items
--------------------
For the purposes of Citehound, we are focusing on the following fields:

* `DescriptorUI <https://www.nlm.nih.gov/mesh/xml_data_elements.html#DescriptorUI>`_
* `DescriptorName <https://www.nlm.nih.gov/mesh/xml_data_elements.html#DescriptorName>`_
* `DescriptorClass <https://www.nlm.nih.gov/mesh/xml_data_elements.html#DescriptorClass>`_
   * The html document does not have the anchor defined (April 2018)
* `DateCreated <https://www.nlm.nih.gov/mesh/xml_data_elements.html#DateCreated>`_
* `DateEstablished <https://www.nlm.nih.gov/mesh/xml_data_elements.html#DateEstablished>`_
* `DateRevised <https://www.nlm.nih.gov/mesh/xml_data_elements.html#DateRevised>`_
* `PreviousIndexingList <https://www.nlm.nih.gov/mesh/xml_data_elements.html#PreviousIndexingList>`_
* `TreeNumberList <https://www.nlm.nih.gov/mesh/xml_data_elements.html#TreeNumberList>`_
* `AllowableQualifiersList <https://www.nlm.nih.gov/mesh/xml_data_elements.html#AllowableQualifiersList>`_
* `HistoryNote <https://www.nlm.nih.gov/mesh/xml_data_elements.html#HistoryNote>`_
* `ScopeNote <https://www.nlm.nih.gov/mesh/xml_data_elements.html#ScopeNote>`_

Although all of these data items are extracted from the XML file, at the moment, everything except :code:`AllowableQualifiersList` 
is processed and ultimately makes it into the database in one form or another.

The fundamental hieararchy
--------------------------
Each :code:`DescriptorUI` is associated with zero or more Tree Numbers (which are stored in :code:`TreeNumberList`).

A tree number is of the form: :code:`C18.452.845.800.300.299`

What is important here is that this is effectively code 299 that is a specialisation of branch 300, which 
in turn is a specialisation of branch 800, which is a specialisation of branch 845, of branch 452 of the branch 
18 (Nutritional and Metabolic Diseases) of branch **C** which is the final top level Tree (Diseases).

Therefore, the fundamental hierarchy results by connecting all of the descriptors (:code:`DescriptorUI`) via 
the connections implied by their Tree Numbers.

However, as it was mentioned before, every DescriptorUI can be associated with one or more 
tree numbers and some times one Descriptor can belong to totally different trees. 

The tree number used above corresponds to the `Frontotemporal Dementia <https://meshb.nlm.nih.gov/record/ui?ui=D057180>`_ 
code and it is associated with the following Tree Numbers:

* C10.228.140.380.266.299
* C10.574.950.300.299
* C18.452.845.800.300.299
* F03.615.400.380.299

That is, three branches from the tree of Diseases and one branch from Mental Disorders.

Dynamic Nature of MeSH
----------------------
The MeSH hieararchy is not static. It has undergone a huge amount of changes since 1966 and it is still being updated 
to this day (2018).

The hieararhcy is **populated by humans and is meant to be used by humans**. This is important when examining the way 
by which the MeSH term changes, to the Tree, are recorded and the implication is that **the hieararchy is human readable 
but not machine readable.**

At any point in time, each one of the term descriptors can be renamed (that is, change its DescriptorName), withdrawn or 
re-branched. For a more extensive description of the subtle ways that the codes can be modified please refer to 
`this document <https://www.nlm.nih.gov/bsd/policy/yep_background.html>`_.

Because of this, it is possible to recall publications that have been indexed by descriptors that do not exist any more or used to 
be known by different names.

This introduces two additional linear data structures that increase the density of the tree as the create further connections 
between the DescriptorUIs.


Other Hieararchies / Data structures
------------------------------------
There are at least three additional structural parts to the MeSH hierarchy co-existing in the same data file. 
These are as follows:

Withdrawn Codes
^^^^^^^^^^^^^^^
Withdrawn codes are :code:`DescriptorUI` that have been assigned to a publication but have been withdrawn from the hierarchy. 
It is very important to include these withdrawn descriptors to the fundamental hierarchy because they might have been referred to by other 
codes still in existence.

Unfortunately, because of the way that the changes are recorded (`in the best case, as an excel or pdf file <https://www.nlm.nih.gov/mesh/filelist.html>`_), 
it is impossible to track the withdrawn codes in time via a single file.

For this reason, a purposely built script is scouring the (approximately) 4.5GB of XML data in all XML files from 2002 onwards and extracts the data for those 
codes that have been withdrawn.

These data are entered into the database **first**, before inserting the latest MeSH hieararchy version that can be obtained simply from NLM.

Renamed / Rebranched Codes
^^^^^^^^^^^^^^^^^^^^^^^^^^
Changes to what codes used to be known as are tracked, in human readable form, by parsing the :code:`HistoryNote` for wach code for expressions of the form:

:code:`was SOMETHING FROM-TO`, where :code:`SOMETHING` is a descriptor's heading and :code:`FROM-TO` a time interval within which the code was known by a different 
name

.. note:: (April 2018) There are additional forms of modifications in existence that are less obvious to dicipher. Questions have been given to the NLM support but no 
           answer so far

Concepts, Terms and Allowable Qualifiers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
These are part of a :code:`DescriptorRecord` and if ingested can enrich the hierarchy further. At the moment, none of these elements are inserted in the Citehound database.

* **Concepts:** Each descriptor is associated with one or more distinct concepts that help indexers (**human beings**) to decide on the right descriptor semantically.
* **Terms:** Each Concept is associated with one or more Terms which are verbatim phrases that describe a particular concept.
* **Allowable Qualifiers** Each Descriptor is specialised further via the use of a Qualifier. Qualifiers are unique and act as properties. Qualifiers can be applied 
  across descriptors and specialise their meaning further.

           
Citehound Schema
-----------------

Citehound represents each descriptor via an :code:`AssociableMeSHTerm` entity. This entity has the fields mentioned in the `Extracted Data Items`_ section and 
a series of relationships as follows:

* :code:`SPECIALISATION_OF`, to represent the fundamental hierarchy
* :code:`ALSO_KNOWN_AS`, to represent other names by which this same code might have been known in the past
* :code:`PREVIOUSLY_KNOWN_AS`, to represent headings that used to be used instead of this code in the past.

* :code:`pubmedArticle` entities are associated with :code:`AssociableMeSHTerm` entities via a :code:`meshTerms` relationship.

This last relationship is the vital link between the articles and the MeSH hierarchy and opens up the gate to very rich queries 
and insights to the database.


Brief Use Case (Sumarise a large set of publications)
-----------------------------------------------------



Conclusion
----------

