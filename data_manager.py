import json
import logging
import os
import typing as tp
from contextlib import closing

import discord
import discord.ext.commands

import database


class DataManager:
    def __init__(self, client: discord.ext.commands.Bot, db: database.Database):
        self.logger = logging.getLogger('discord')
        self.client = client
        self.database = db

        self.servers_opted_in: tp.Set[int] = set()

        with open(os.path.join('assets', 'server-opt-in.json'), 'r') as f:
            data_opt_in = json.load(f)
        [self.servers_opted_in.add(server_id) for server_id in data_opt_in['server_ids']]

        self.client.add_listener(self.tally_message, 'on_message')

        self.messages_table_name: str = 'messages'
        self.user_column_name: str = 'user_id'
        self.server_column_name: str = 'server_id'
        self.time_column_name: str = 'sent_time'
        self.message_column_name: str = 'message_id'

    def is_server_opted_in(self, server_id: int) -> bool:
        return server_id in self.servers_opted_in

    async def is_user_cool_with_data(self, user: discord.Member, server_id: int) -> bool:
        guild: discord.Guild = self.client.get_guild(server_id)

        cool_with_data_role: discord.Role = discord.utils.get(guild.roles, name='Cool With Data')

        if len(cool_with_data_role.members) <= 0:
            self.logger.warning(f'Cool With Data role is empty!')
            return False

        self.logger.info(f'Cool with data role is {cool_with_data_role.name}, {len(cool_with_data_role.members)}')

        return cool_with_data_role in user.roles

    async def tally_message(self, context: discord.ext.commands.Context):
        can_tally_message: bool = self.is_server_opted_in(context.guild.id) and await self.is_user_cool_with_data(
            context.author, context.guild.id)

        self.logger.info(f'Can we tally the message from {context.author.id}? {can_tally_message}')

        if can_tally_message:
            with closing(self.database.get_connection()) as connection:
                with closing(connection.cursor()) as cursor:
                    cursor.execute(
                        f'insert into {self.messages_table_name} ({self.message_column_name}, {self.user_column_name}, {self.server_column_name}, {self.time_column_name}) values (?, ?, ?, ?)',
                        [context.message.id, context.author.id, context.guild.id, context.message.created_at])
                connection.commit()
