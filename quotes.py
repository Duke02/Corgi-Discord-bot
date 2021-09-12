import datetime
import typing as tp
from contextlib import closing

from abstract_database import AbstractDatabase


class QuotesDatabase(AbstractDatabase):
    def __init__(self):
        super(QuotesDatabase, self).__init__('quotes', 'quotes')

    def add_quote(self, quote: str, author: str, time: tp.Optional[float] = None):
        if time is None:
            time = datetime.datetime.now().timestamp()

        self.execute(f'insert into {self.table_name} values(?, ?, ?)', (quote, author, str(time)))

    def get_random_quote(self):
        with closing(self.get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(f'select * from {self.table_name} order by random() limit 1;')
                quote = cursor.fetchone()
                return f'{datetime.datetime.fromtimestamp(float(quote[2])):%B %d, %Y %H:%M:%S}: {quote[1]} said, "{quote[0]}"'
