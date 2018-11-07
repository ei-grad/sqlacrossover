sqlacrossover
=============

Cross-database migration tool based on SQLAlchemy

Features:

* Copy data and schema between SQLAlchemy-supported databases
* Table ordering - taking the foreign keys dependencies in consideration
* Data processing in batches
* Wrap the process in transaction to get consistent results
* Dump schema and data to SQL file

Installation
------------

.. code-block:: bash

    pip install sqlacrossover[MySQL,PostgreSQL]

Example
-------

.. code-block:: bash

    sqlacrossover 'mysql+pymysql:///sourcedatabase?charset=utf8' postgresql:///targetdatabase

TODO
----

* Write documentation

* Implement options:

  * ``--no-data``
  * ``--tables``
  * ``--exclude-tables``
  * ``--truncate-non-empty``
  * ``--skip-non-empty``

* Implement efficient driver-depenedent insert methods

  * PostgreSQL ``COPY FROM`` / ``COPY TO``
  * MySQL ``LOAD DATA LOCAL INFILE``

* Write tests, configure travis.ci

Contibuting
-----------

Pull requests implementing new features, adding tests, docs and fixing bugs are welcome.

Feel free to open an issue with any feedback or ideas, also.
