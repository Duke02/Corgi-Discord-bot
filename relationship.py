import typing as tp
from contextlib import closing
import datetime as dt

from abstract_database import AbstractDatabase


class RelationshipDatabase(AbstractDatabase):
    def __init__(self):
        super(RelationshipDatabase, self).__init__('relations', 'relations')
        self.user_id_column = 'user_id'
        self.affection_column = 'affection'
        self.updated_time_column = 'last_update'

    def add_affection(self, user_id: int, delta_affection: int):
        sql_statement: str = f'select {self.affection_column} from {self.table_name} where {self.user_id_column} = ? limit 1;'
        self.logger.info(f'Connecting to relationship database at: "{self.connection_url}"')
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                self.logger.info(f'Using SQL query for affection: "{sql_statement}"')
                cursor.execute(sql_statement, [user_id])
                current_affection: int = cursor.fetchone()[0]

            new_affection: int = current_affection + delta_affection
            update_time: dt.datetime = dt.datetime.now()

            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    f'update {self.table_name} set {self.affection_column} = ?, {self.updated_time_column} = ? where {self.user_id_column} = ?',
                    [new_affection, update_time, user_id])
            connection.commit()

    def get_most_loved(self, top_n: int = 10) -> tp.List[tp.Dict[str, int]]:
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    f'select {self.user_id_column}, {self.affection_column} from {self.table_name} order by {self.affection_column} desc limit {top_n};')
                rows = cursor.fetchmany(top_n)
                output = []
                for row in rows:
                    output.append({'user_id': row[self.user_id_column], 'affection': row[self.affection_column]})
        return output

    def get_affection(self, user_id: int) -> tp.Tuple[int, int]:
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                max_name: str = 'max_affection'
                cursor.execute(
                    f'select {self.affection_column}, max({self.affection_column}) as {max_name} from {self.table_name} where {self.user_id_column} = ? limit 1',
                    [user_id])
                row = cursor.fetchone()
                affection: int = row[self.affection_column]
                max_affection: int = row[max_name]
                return affection, max_affection

    def get_max_affection(self) -> int:
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                max_name: str = 'max_affection'
                cursor.execute(
                    f'select max({self.affection_column}) as {max_name} from {self.table_name} limit 1')
                row = cursor.fetchone()
                max_affection: int = row[max_name]
                return max_affection
