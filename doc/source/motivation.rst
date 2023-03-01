==========
Motivation
==========

The primary motivation for putting together Citehound was the sheer amount of repetitive tasks we found ourselves
doing while trying to process bibliographical data.

Why analyse bibliographical data?
=================================

.. todo::
    Motivation for bib data analysis in general

Starting from scratch
=====================

Here is a small snippet of all the attributes that are associated with an academic paper in the Pubmed data base.

.. literalinclude:: resources/code_examples/pubmed_sample_full.xml

The most natural reaction to anyone who may have browsed a Pubmed XML file with a view to analysing its contents,
is to go "Alright, let's write a script to extract the data we are after".

There is absolutely no doubt that simple Python programs can be written to parse and extract some parameters of interest
out of these data and analyse it.

The fun bit starts when feature creep starts settling in and investigators start asking for more parameters, more
inference, more accuracy and so on. Suddenly, that XML Python script with the 72 ad-hoc additions it suffered on its way
to publishing that one "proof-of-concept" paper shows its limitations.

.. todo::
    Mention existing libraries for bibliographical data here

Even existing tools leave a lot of work up to the researcher especially when it comes to pre-processing and
data linkage.

