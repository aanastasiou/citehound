Adding Open Citations Support
=============================

Open citations is a huge dataset that is available from `this link <http://opencitations.net/download>`_.

While the `full model <http://opencitations.net/model>`_ is useful the main thing to remember is that the 
`data.csv` file contains 5 columns:

1. oci
    * A unique identifier of the resource described
2. citing
    * The DOI of the citing paper
3. cited
    * The DOI of the cited paper
4. creation
    * When this association was created
5. timespan
    * Timespan during which the association was valid
    
    
There are other datafiles that describe the rest of the model's entities but for the purposes of deriving 
co-citation networks the simplistic approach is to match the DOI of the citing paper and retrieve the cited.

So, the key problem now is how to do this efficiently.


Working with the OC dataset
---------------------------

The dataset is massive (~50GB) but `sqlite` seems to be able to handle it well.

Installation
^^^^^^^^^^^^
Prior to starting the installation make sure that you have at least 300GB of disk space available and `sudo apt-get install sqlite3` 
and optionally `sqlitestudio <https://sqlitestudio.pl/index.rvt>`_ too.

1. Download the dataset `data.zip`
2. Decompress it. At this point the dataset is ~50GB.
3. Start sqlite3 and run the following script::

    BEGIN;
    CREATE TABLE OC_citations(
      "oci" TEXT,
      "citing" TEXT,
      "cited" TEXT,
      "creation" TEXT,
      "timespan" TEXT
    );
    CREATE INDEX onciting ON OC_citations(citing);
    COMMIT;
    
This is not entirely accurate but it will work for the purposes of a simple test.

4. From within sqlite3::
    
    `.mode csv`
    `.import data.csv OC_citations`
    
This will create a file that is approximately 72GB long. At this point `data.csv` can be erased.

Querying
^^^^^^^^
Use standard SQL to query the file.
