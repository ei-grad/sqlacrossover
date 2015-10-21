#!/usr/bin/env python

import argparse

import sqlalchemy as sa
from sqlalchemy.engine import reflection


class Connection():
    def __init__(self, url):
        self.engine = sa.create_engine(url)
        self.conn = self.engine.connect()
        self.meta = sa.MetaData()
        self.meta.reflect(self.engine)
        self.insp = reflection.Inspector.from_engine(self.engine)
        self.tables = self.insp.get_sorted_table_and_fkc_names()


class Crossover():

    def __init__(self, source, target, bulk):
        self.source = Connection(source)
        self.target = Connection(target)
        self.bulk = bulk

        # TODO: implement insert_data_copy
        self.insert_data = self.insert_data_simple

    def copy_data(self):
        assert self.source.tables[-1][0] is None
        for table, fks in self.source.tables[:-1]:
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
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('source', help='Source database SQLAlchemy URL')
    parser.add_argument('target', help='Target database SQLAlchemy URL')
    parser.add_argument('--bulk', metavar="N", default=10000, help='Iterate by N rows')
    args = parser.parse_args()
    crossover = Crossover(args.source, args.target, bulk=args.bulk)
    crossover.copy_data()


if __name__ == '__main__':
    main()
