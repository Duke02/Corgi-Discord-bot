import datetime as dt
import logging
import os.path
import sqlite3
import typing as tp
from contextlib import closing
from pathlib import Path

from utils import get_db_directory


class Database:
    def __init__(self):
        self.logger = logging.getLogger('discord')
        self.connection_url: Path = get_db_directory() / 'corgi.db'  # os.path.abspath(os.path.join('db', 'corgi.db'))

        self.server_id_column: str = 'server_id'

        self.quotes_table_name: str = 'quotes'
        self.quote_column_name: str = 'quote'
        self.author_column_name: str = 'author'
        self.time_column_name: str = 'time'

        self.relation_table_name: str = 'relations'
        self.user_id_column = 'user_id'
        self.affection_column = 'affection'
        self.updated_time_column = 'last_update'

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

    def add_quote(self, quote: str, author: str, server_id: int, time: tp.Optional[float] = None):
        if time is None:
            time = dt.datetime.now().timestamp()

        self.execute(f'insert into {self.quotes_table_name} values(?, ?, ?, ?)', (quote, author, str(time), server_id))

    def get_random_quote(self, server_id: int):
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    f'select * from {self.quotes_table_name} where {self.server_id_column} = ? order by random() limit 1;',
                    [server_id])
                quote = cursor.fetchone()
                return f'{dt.datetime.fromtimestamp(float(quote[2])):%B %d, %Y %H:%M:%S}: {quote[1]} said, "{quote[0]}"'

    def add_affection(self, user_id: int, delta_affection: int, server_id: int):
        sql_statement: str = f'select {self.affection_column} from {self.relation_table_name} where {self.user_id_column} = ? and {self.server_id_column} = ? limit 1;'
        self.logger.info(f'Connecting to relationship database at: "{self.connection_url}"')
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                self.logger.info(f'Using SQL query for affection: "{sql_statement}"')
                cursor.execute(sql_statement, [user_id, server_id])
                row = cursor.fetchone()

            update_time: dt.datetime = dt.datetime.now()

            if row is None:
                insert_sql: str = f'insert into {self.relation_table_name} values(?, ?, ?, ?)'
                self.logger.info(f'Creating a new entry into the {self.relation_table_name} table!')
                with closing(connection.cursor()) as cursor:
                    cursor.execute(insert_sql, [user_id, delta_affection, update_time, server_id])
            else:
                current_affection: int = row[0]

                new_affection: int = current_affection + delta_affection

                with closing(connection.cursor()) as cursor:
                    cursor.execute(
                        f'update {self.relation_table_name} set {self.affection_column} = ?, {self.updated_time_column} = ? where {self.user_id_column} = ? and {self.server_id_column} = ?',
                        [new_affection, update_time, user_id, server_id])
            connection.commit()

    def get_most_loved(self, server_id: int, top_n: int = 10) -> tp.List[tp.Dict[str, int]]:
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    f'select {self.user_id_column}, {self.affection_column} from {self.relation_table_name} where {self.server_id_column} = ? order by {self.affection_column} desc limit {top_n};',
                    [server_id])
                rows = cursor.fetchmany(top_n)
                output = []
                for row in rows:
                    output.append({'user_id': row[0], 'affection': row[1]})
        return output

    def get_affection(self, user_id: int, server_id: int) -> int:
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    f'select {self.affection_column} from {self.relation_table_name} where {self.user_id_column} = ? and {self.server_id_column} = ? limit 1',
                    [user_id, server_id])
                row = cursor.fetchone()
                if row is None:
                    return 0
                affection: int = row[0]
                return affection

    def get_max_affection(self, server_id: int) -> int:
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                max_name: str = 'max_affection'
                cursor.execute(
                    f'select max({self.affection_column}) as {max_name} from {self.relation_table_name} where {self.server_id_column} = ? limit 1',
                    [server_id])
                row = cursor.fetchone()
                max_affection: int = row[0]
                return max_affection


"""
This doesn't work but should give you an idea of how to make a select query.
    def get(self, sql_query: str):
        
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(sql_query)
                yield cursor.fetchone()
"""
