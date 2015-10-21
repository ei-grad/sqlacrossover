#!/usr/bin/env python

import argparse
import logging

import sqlalchemy as sa


logger = logging.getLogger(__name__)


class Connection():
    def __init__(self, url):
        self.engine = sa.create_engine(url)
        self.conn = self.engine.connect()
        self.meta = sa.MetaData()
        self.meta.reflect(self.engine)

        tables = sa.schema.sort_tables(self.meta.tables.values())
        self.tables = [i.name for i in tables]


class Crossover():

    def __init__(self, source, target, bulk):
        self.source = Connection(source)
        self.target = Connection(target)
        self.bulk = bulk

        # TODO: implement insert_data_copy
        self.insert_data = self.insert_data_simple

    def copy_data_in_transaction(self):
        with self.target.conn.begin():
            self.copy_data()

    def copy_data(self):
        if set(self.source.tables) != set(self.target.tables):
            logger.warning("Source and target database table lists are not identical!")
        for table in self.source.tables:
            if table in self.target.tables:
                self.copy_table(table)

    def copy_table(self, table):
        offset = 0
        source_table = self.target.meta.tables[table]
        while True:
            data = list(self.source.conn.execute(
                sa.select([source_table]).offset(offset).limit(self.bulk)
            ))
            if not data:
                break
            self.insert_data(table, data)
            offset += self.bulk

    def insert_data_simple(self, table, data):
        self.target.conn.execute(self.target.meta.tables[table].insert(), data)


def main():
    logging.basicConfig(format="[%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('source', help='Source database SQLAlchemy URL')
    parser.add_argument('target', help='Target database SQLAlchemy URL')
    parser.add_argument('--bulk', metavar="N", default=10000,
                        help='Iterate by N rows')
    parser.add_argument('--no-transaction', dest='use_transaction',
                        action='store_false',
                        help="Don't wrap inserts in a single transaction")
    args = parser.parse_args()
    crossover = Crossover(args.source, args.target, bulk=args.bulk)

    if args.use_transaction:
        crossover.copy_data_in_transaction()
    else:
        crossover.copy_data()


if __name__ == '__main__':
    main()
