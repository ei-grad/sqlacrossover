# sqlacrossover
SQLAlchemy-based cross-database migration tool

It is already better than py-mysql2pgsql, since it process tables in the right
order. But its only feature for now is to copy data, since I only needed it to
migrate data from MySQL to PostgreSQL database with identical schema, which is
managed by Doctrine ORM.

# Installation

    pip install sqlacrossover[MySQL,PostgreSQL]

# Example

    sqlacrossover 'mysql+pymysql:///sourcedatabase?charset=utf8' postgresql:///targetdatabase

# TODO

## Write documentation

## Implement options:

* --create-tables
* --copy-data
* --tables
* --exclude-tables
* --truncate-non-empty
* --skip-non-empty

## Implement efficient driver-depenedent insert methods

* PostgreSQL copy
* ... what else?..
