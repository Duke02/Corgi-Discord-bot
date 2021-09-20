import json
import logging
import os
import pickle
import re
import typing

import discord
import spotipy as sp
from discord.ext import commands


class PlaylistManager(commands.Cog, name='Playlist Manager'):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('discord')
        scopes: typing.List[str] = ['playlist-modify-public']

        spotify_credentials_path: str = os.path.join('assets', 'spotify_credentials.json')
        self.saved_playlist_path: str = os.path.join('assets', 'playlist_id.json')

        if not os.path.exists(spotify_credentials_path):
            self.logger.error(f'Cannot find Spotify Credentials at path: "{spotify_credentials_path}"')
            self.can_work: bool = False
            return

        self.can_work: bool = True

        self.music_channel: typing.Optional[discord.abc.GuildChannel] = None
        self.id_of_playlist_to_create: str = ''

        self.is_enabled: bool = self.music_channel is not None and len(self.id_of_playlist_to_create) > 0

        if not self.is_enabled and os.path.exists(self.saved_playlist_path):
            self.logger.error(
                f'There was a problem loading the previous playlist data from file! Disabling playlist manager.')

        with open(spotify_credentials_path, 'r') as f:
            credentials: typing.Dict[str, str] = json.load(f)

            self.user_id: str = credentials['user_id']

            oauth: sp.SpotifyOAuth = sp.SpotifyOAuth(client_id=credentials['client_id'],
                                                     client_secret=credentials['client_secret'],
                                                     redirect_uri=credentials['redirect_url'],
                                                     scope=','.join(scopes))
            self.spotify_client = sp.Spotify(auth_manager=oauth)

    async def setup_music_channel(self):
        self.logger.info(f'Setting up music channel!')
        with open(self.saved_playlist_path, 'rb') as f:
            data: typing.Dict[str, str] = pickle.load(f)
            self.id_of_playlist_to_create = data['playlist_id']

            music_channel_id: int = int(data['music_channel_id'])
            self.music_channel = await self.bot.fetch_channel(music_channel_id)
        self.is_enabled: bool = True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if os.path.exists(self.saved_playlist_path) and not self.is_enabled:
            await self.setup_music_channel()

        if not self.can_work or not self.is_enabled or message.author.bot:
            return

        if len(self.id_of_playlist_to_create) <= 0:
            return

        if message.channel.id != self.music_channel.id:
            return

        spotify_regex: re.Pattern = re.compile(
            r'https://open.spotify.com/(?P<link_type>track|album|playlist)/(?P<id>[0-9A-Za-z]+)(?:\?.+)?')

        # Key: type of link, Value: list of ids
        found_matches: typing.Dict[str, typing.List[str]] = dict()

        found_matches['track'] = []
        found_matches['album'] = []
        found_matches['playlist'] = []

        for match in spotify_regex.finditer(message.content):
            if match is None or not match:
                continue

            found_matches[match['link_type']].append(match['id'])

        all_tracks_to_add: typing.List[str] = found_matches['track']

        for album_id in found_matches['album']:
            album_tracks: typing.List[typing.Dict] = self.spotify_client.album_tracks(album_id=album_id)['items']
            track_ids: typing.List[str] = list(map(lambda track: track['id'], album_tracks))
            all_tracks_to_add.extend(track_ids)

        for playlist_id in found_matches['playlist']:
            response: typing.Dict = self.spotify_client.playlist_items(playlist_id=playlist_id)
            playlist_tracks: typing.List[typing.Dict] = response['items']

            while response['next']:
                response = self.spotify_client.next(response)
                playlist_tracks.extend(response['items'])

            track_ids: typing.List[str] = list(map(lambda track: track['track']['id'], playlist_tracks))
            all_tracks_to_add.extend(track_ids)

        current_tracks_response: typing.Dict = self.spotify_client.playlist_items(
            playlist_id=self.id_of_playlist_to_create)

        current_tracks: typing.List[str] = list(map(lambda track: track['track']['id'],
                                                    current_tracks_response['items']))

        while current_tracks_response['next']:
            current_tracks_response: typing.Dict = self.spotify_client.next(current_tracks_response)
            current_tracks.extend(list(map(lambda track: track['track']['id'],
                                           current_tracks_response['items'])))

        # Make sure we're not adding duplicate tracks.
        all_tracks_to_add: typing.List[str] = list(set(all_tracks_to_add) - set(current_tracks))

        n_tracks_to_add: int = len(all_tracks_to_add)

        # Add tracks in batches of 100.
        while len(all_tracks_to_add) > 0:
            current_batch: typing.List[str] = all_tracks_to_add[:100]
            self.spotify_client.playlist_add_items(playlist_id=self.id_of_playlist_to_create,
                                                   items=current_batch)
            all_tracks_to_add = list(set(all_tracks_to_add) - set(current_batch))

        if n_tracks_to_add > 0:
            await message.channel.send(
                f'I ADDED {n_tracks_to_add} SONGS TO THE SPOTIFY PLAYLIST!!!!! DO `{self.bot.command_prefix}playlist` TO GET A LINK! dO I GET TREATS NOW?????////')

    @commands.group(name='playlist')
    async def _parent_playlist_command(self, context: commands.Context):
        if context.invoked_subcommand is None:
            await self.give_playlist_link(context)

    @_parent_playlist_command.command(name='enable')
    async def enable_playlist(self, context: commands.Context, playlist_name: str):
        if not context.author.guild_permissions.administrator:
            await context.send(f'You bit off more than you can chew pardner...\nWANNA GRAB A BIG STICK WITH ME')
            return

        if not self.is_enabled and os.path.exists(self.saved_playlist_path):
            await self.setup_music_channel()

        if self.is_enabled or not self.can_work:
            await self.give_playlist_link(context, message=f'Sorry! But the Playlist Manager has already been'
                                                           ' enabled! You can find the playlist here')
            return

        self.music_channel: discord.TextChannel = context.channel
        response: typing.Dict = self.spotify_client.user_playlist_create(user=self.user_id, name=playlist_name,
                                                                         description=f'The mega playlist for all songs from '
                                                                                     f'" #{self.music_channel.name} in {context.guild.name}')
        self.id_of_playlist_to_create = response['id']
        self.is_enabled: bool = True

        spotify_data: typing.Dict[str, str] = {
            'playlist_id': self.id_of_playlist_to_create,
            'music_channel_id': context.channel.id,
        }

        with open(self.saved_playlist_path, 'wb') as f:
            pickle.dump(spotify_data, f)

        await self.give_playlist_link(context, message=f'Just created that playlist for you!')

    @_parent_playlist_command.command(name='link')
    async def give_playlist_link(self, context: commands.Context, message: str = 'Here\'s the link!'):
        if self.can_work and self.is_enabled:
            playlist_link: typing.Dict[str, str] = \
                self.spotify_client.playlist(playlist_id=self.id_of_playlist_to_create,
                                             fields='external_urls[spotify]')['external_urls']['spotify']
            await context.send(f'{message}\n{playlist_link}')
        else:
            await context.send(f'Sorry! But the playlist manager hasn\'t been set up yet!'
                               f' Please do `{self.bot.command_prefix}playlist enable` to enable it!')
