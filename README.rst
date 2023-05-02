Citehound
=========

Your literature search results are in the order of hundreds or even thousands of articles.

How are you going to make sense of this literature dataset?  


Citehound brings together datasets and methods for working with literature datasets to:

1. Discover prolific authors / institutes / countries in a given dataset
2. Track affiliations over a period of time
2. Extract co-authorship networks (i.e. who is working with whom)
3. Assess the popularity of topics
4. Extract articles of specific authors / institutes / countries from specific years...

And if the built-in queries are not flexible enough for your research, you can of course run your own.


The project is not affiliated with `NCBI <https://www.ncbi.nlm.nih.gov/>`_ but due to the wide 
availability of its datasets, `PubMed <https://pubmed.ncbi.nlm.nih.gov/>`_ is supported widely.


Citehound's data model brings together three datasets:

1. A bibliographical data source

   * PubMed, for the moment, (but have also mapped `ERIC <https://eric.ed.gov/>`_ and `dblp <https://dblp.org/>`_ on 
     Citehound's data model).

2. The full `MeSH <https://meshb.nlm.nih.gov/>`_ hierarchy.

3. The Registry Of Research organisations (`ROR <https://ror.org/>`_).

Citehound's code manages the full round trip of fetching and ingesting datasets from various sources,
links affiliations to their ROR identifiers and runs queries on the database.

Use Citehound as an aid to your literature search or literature review writing or as a basis for 
applications making use of bibliographical data.

Installation
------------

1. Clone the repository
2. Create a virtualenv
3. Activate the virtualenv
4. Install requirements (``> pip install -r requirements.txt``)
5. Install citehound (``> pip install ./``)
6. Configure citehound


