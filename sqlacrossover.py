#!/usr/bin/env python

import argparse
import logging
import sys

import sqlalchemy as sa


logger = logging.getLogger(__name__)


class GenericDatabase():
    def __init__(self, url):
        self.engine = sa.create_engine(url)
        self.conn = self.engine.connect()
        self.meta = sa.MetaData()
        self.meta.reflect(self.engine)

    def __iter__(self):
        return iter(sa.schema.sort_tables(self.meta.tables.values()))


class GenericSource(GenericDatabase):
    def select(self, table, offset, batch_size):
        return self.conn.execute(
            sa.select([table])
            .order_by(*table.primary_key.columns)
            .offset(offset)
            .limit(batch_size)
        )


class GenericTarget(GenericDatabase):

    def create_all(self, metadata):
        metadata.create_all(self.engine)

    def could_adopt(self, target_table_name, source_table):
        # XXX: implement a generic table structure equality checking
        # raise NotImplementedError()
        return True

    def insert(self, target_table_name, source_table, data):
        # XXX: replace table name by target_table_name
        # XXX: source_table is used to keep the columns order
        data = list(map(dict, data))
        if len(data) > 0:
            return self.conn.execute(source_table.insert(), data).rowcount
        return len(data)


class FileTarget():

    def __init__(self, fileobj, dialect):
        self.fileobj = fileobj
        self.dialect = dialect

    def create_all(self, metadata):
        for table in sa.schema.sort_tables(metadata.tables.values()):
            ddl = sa.schema.CreateTable(table)
            ddl = self.dialect.ddl_compiler(self.dialect, ddl)
            self.fileobj.write('%s;\n\n' % (
                ddl.string.strip(),
            ))

    def could_adopt(self, target_table_name, source_table):
        return True

    def insert(self, target_table_name, source_table, data):
        count = 0
        for row in data:
            count += 1
            row = {k: v for k, v in zip(row.keys(), row) if v is not None}
            stmt = source_table.insert().values(row)
            stmt = stmt.compile(
                dialect=self.dialect,
                compile_kwargs={"literal_binds": True}
            )
            self.fileobj.write('%s;\n' % (stmt,))
        return count

    def close(self):
        self.file.close()


class Crossover():

    def __init__(self, source, target, batch_size):
        self.source = source
        self.target = target
        self.batch_size = batch_size

    def run_in_transaction(self):
        with self.source.conn.begin():
            with self.target.conn.begin():
                self.run()

    def run(self):
        for table in self.source:
            if self.target.could_adopt(table.name, table):
                self.copy_table(table)
            else:
                logger.error("Skipping table %s", table.name)

    def copy_table(self, table):
        offset = 0
        while True:
            data = self.source.select(table, offset, self.batch_size)
            rows_count = self.target.insert(table.name, table, data)
            if rows_count == 0:
                break
            offset += rows_count


def main():
    logging.basicConfig(format="[%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('source', help='Source database SQLAlchemy URL')
    parser.add_argument('target', help='Target database SQLAlchemy URL')
    parser.add_argument('--create-all', action='store_true',
                        help='Create tables in target database')
    parser.add_argument('--batch-size', metavar="N", default=10000,
                        help='Iterate by N rows')
    parser.add_argument('--no-transaction', dest='use_transaction',
                        action='store_false',
                        help="Don't wrap inserts in a single transaction")
    args = parser.parse_args()

    source = GenericSource(args.source)
    fileobj = None
    if args.target.startswith('file://'):
        fileobj = open(args.target[7:], 'w')
        target = FileTarget(fileobj, dialect=source.engine.dialect)
    elif args.target == '-':
        target = FileTarget(sys.stdout, dialect=source.engine.dialect)
    # TODO: implement PostgreSQLTarget
    else:
        target = GenericTarget(args.target)

    if args.create_all:
        if not hasattr(target, 'create_all'):
            sys.stderr.write("%s: create_all is not implemented" %
                             type(target))
            return 1
        if not hasattr(source, 'meta'):
            sys.stderr.write("%s: no metadata available for create_all" %
                             type(source))
            return 1
        for table in source.meta.tables.values():
            for c in table.columns:
                if c.autoincrement:
                    # remove postgresql's `nextval(...)` server defaults which
                    # duplicates the reflected autoincrement value, and is not
                    # supported in other dialects
                    c.server_default = None
        target.create_all(source.meta)

    crossover = Crossover(source, target, batch_size=args.batch_size)

    if args.use_transaction:
        crossover.run_in_transaction()
    else:
        crossover.run()

    if fileobj is not None:
        fileobj.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
