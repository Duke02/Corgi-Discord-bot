import datetime
import logging
import os.path
import sqlite3
import typing as tp
from contextlib import closing


class AbstractDatabase:
    def __init__(self, database_name: str, table_name: str):
        self.logger = logging.getLogger('discord')

        self.connection_url = os.path.abspath(os.path.join('db', f'{database_name}.db'))
        self.table_name: str = table_name

    def get_connection(self):
        try:
            self.logger.info(f'Connecting to quotes database at connection URL "{self.connection_url}"...')
            connection = sqlite3.connect(self.connection_url)
            self.logger.info(f'Connected successfully!')
            return connection
        except sqlite3.Error as e:
            self.logger.error(f'Could not connect to database. Error: {e}')
            return None

    def execute(self, sql_query: str, params: tp.Iterable, *args):
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(sql_query, params)
            connection.commit()


"""
This doesn't work but should give you an idea of how to make a select query.
    def get(self, sql_query: str):
        
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(sql_query)
                yield cursor.fetchone()
"""
