import datetime
import logging
import math
import os
import random
import re
import typing as tp
from pathlib import Path
from time import sleep

sleep(10)

from dotenv import load_dotenv

from corgi_bot.utils import get_logs_directory

load_dotenv()

import discord
from discord.ext import commands

from corgi_bot import playlist_manager
from corgi_bot.database import Database

PREFIX: str = '$'
intents = discord.Intents.default()
intents.message_content = True 
intents.messages = True 
intents.reactions = True 
intents.guild_messages = True 
intents.guild_reactions = True 

client: commands.Bot = commands.Bot(command_prefix=PREFIX, intents=intents)

logger: logging.Logger = logging.getLogger('discord')


def setup():
    logging_filename: Path = get_logs_directory() / f'{datetime.datetime.now():%Y%m%d_%H%M%S%f}.log'

    print(f'[{logging_filename=}]')

    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename=logging_filename, encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s|%(name)s]: %(message)s'))
    logger.addHandler(handler)


setup()

database: Database = Database()


# data_mngr: data_manager.DataManager = data_manager.DataManager(client, database)
# client.add_listener(data_mngr.tally_message, 'on_message')


@client.command()
async def roll(context: commands.Context, die: str) -> None:
    """
    Roll some dice with something like 3d6
    :param die: A string in the format of NdS where N is the # of dice to roll, S is the number of sides per die.
    """
    d_index: int = die.find('d')
    num_dice: int = int(die[:d_index])
    num_faces: int = int(die[d_index + 1:])

    rolls: tp.List[int] = [random.randint(1, num_faces) for _ in range(num_dice)]
    await context.send(f'You rolled a {sum(rolls)}! (Individual rolls: {", ".join([str(r) for r in rolls])})')


@client.group()
async def quote(context: commands.Context):
    """
    Gets a random quote that's been saved.
    """
    if context.invoked_subcommand is None:
        await _quote_get(context)


@quote.command(name='get')
async def _quote_get(context: commands.Context):
    """
    Gets a random quote that's been saved.
    """
    quote_got = database.get_random_quote(context.guild.id)
    await context.send(quote_got)


@quote.command(name='store')
async def _quote_store(context: commands.Context, actual_quote: str, author: tp.Optional[str]):
    """
    Run with `quote store "<the quote>" [author name]`
    :param actual_quote: The quote to store. Use "'s to do multiple words.
    :param author: (Optional) The person that said the quote. Use "'s for multiple name parts(???)
    """
    time = datetime.datetime.now().timestamp()
    database.add_quote(actual_quote, author, context.guild.id, time)
    await context.send(
        f'Stored quote!\nTime: {datetime.datetime.fromtimestamp(time):%B %d, %Y %H:%M:%S}, Author: {author}, Quote: {actual_quote}')


@client.command()
async def ping(context: commands.Context):
    """
    Ping! Pong!
    """
    sent_time = context.message.created_at
    current_time = datetime.datetime.now().astimezone(datetime.timezone.utc)

    await context.send(
        f'I BROUGHT THE BALL BACK IN {(current_time - sent_time).microseconds / 1e3}MS! DO I GET A TREAT?')


@client.command()
async def ball(context: commands.Context):
    """
    Throw the ball for Corgi Bot!
    """
    database.add_affection(context.message.author.id, 1, context.guild.id)
    await ping(context)


@client.command()
async def affection_list(context: commands.Context, n: int = 10):
    """
    List out who loves Corgi Bot the best!
    :param n: The number of people in the list. (Default is 10)
    """
    top_affection: tp.List[tp.Dict[str, int]] = database.get_most_loved(context.guild.id, n)
    relevant_users = [(await client.fetch_user(user_aff['user_id']), user_aff['affection']) for user_aff in
                      top_affection]

    relevant_users = [(user.display_name, aff) for user, aff in relevant_users]

    await context.send(
        f'Top {n} most loved people... BY ME!!!\n' + '\n'.join([f'{k} : {v}' for k, v in relevant_users]))


@client.command()
async def affection(context: commands.Context):
    """
    Figure out how much Corgi Bot loves you (or someone else if you tag them)
    """
    message: discord.Message = context.message

    id_to_use: int = message.mentions[0].id if len(message.mentions) > 0 else context.author.id

    try:
        user_affection: int = database.get_affection(id_to_use, context.guild.id)
    except TypeError:
        user_affection: int = 0

    is_max_affection: bool = database.get_max_affection(context.guild.id) == user_affection
    user: discord.User = message.mentions[0] if len(message.mentions) > 0 else context.author
    message: str = f'{user.mention} I LOVE YOU {user_affection} TIMES MORE THAN PETS!!!!!!'
    if is_max_affection:
        message += '\n||Don\'t tell anyone but I love you the most!||'
    await context.send(message)


@client.command()
async def hello(context: commands.Context):
    """
    Say hi to Corgi Bot!
    """
    await context.send(f'Hello there {context.message.author.mention}!!! Will you give me pets?????')


def anti_cheat_limit(n: int, limit: int, affection_per: int, positive_message: str, neutral_message: str,
                     negative_message: str) -> tp.Tuple[int, str]:
    if n <= limit:
        return affection_per * n, positive_message
    elif limit < n <= (limit * 10):
        return affection_per * limit, neutral_message
    else:
        return - affection_per * n // limit + affection_per * limit, negative_message


@client.command()
async def pet(context: commands.Context, n_pets: int = 1):
    """
    Pet Corgi Bot a number of times!
    :param n_pets: How many times you want to pet Corgi Bot (Optional, default is 1)
    """
    delta, message = anti_cheat_limit(n_pets, 7, 3, 'I LOVE PETS SO MUCH BUT NOT AS MUCH AS I LOVE YOU!!!!!!!!!!!',
                                      'Hey you have a lot of hands for a hooman...\nBUT OK!',
                                      "Foolish mortal. Your abuses of physics and anatomy have become entirely too apparent to my omniscient being. Prepare to be punished.")
    database.add_affection(context.message.author.id, delta, context.guild.id)
    await context.send(message)


@client.command()
async def treat(context: commands.Context, n_snackies: int = 1):
    """
    Give Corgi Bot a bunch of snackies!!!!
    :param n_snackies: The number of SNACKIES(!!!) you want to give Corgi Bot (Optional, default is 1)
    """
    delta, message = anti_cheat_limit(n_snackies, 10, 5, f"SNACKIES I LOVE THME SO ,MUCH!!!!!!!!!",
                                      "Oof I may be gaining some weight... \nBUT TREATS ARE WORTH IT",
                                      "How dare you make me 1,153,482 lbs?!!!!!! I'm a corgi!!!!!1")
    database.add_affection(context.message.author.id, delta, context.guild.id)
    await context.send(message)


@client.command()
async def apologize(context: commands.Context):
    """
    Did you piss off Corgi Bot? Apologize and maybe he'll forgive you.
    """
    user_affection: int = database.get_affection(context.author.id, context.guild.id)

    if user_affection >= 0:
        await context.send("WHY FORGIVE??? I LOVE YOU AND ALWAYS HAVE :)")
        return

    max_affection: int = database.get_max_affection(context.guild.id)
    chance: float = math.sqrt(abs(user_affection)) / max_affection
    if chance > 1:
        # No greater sin has been commited than to be more hated than the most loved.
        chance = 1e-16
    sample: float = random.random()
    forgiven: bool = sample < chance

    if forgiven:
        database.reset_affection(context.author.id, context.guild.id)
        await context.send('AWWW I COULD NEVER STAY MAD AT YOU!! I LOVE YOU <3 LET\'S GO FOR WALKIES!!!!')
    elif (sample - chance) > (1 - 1e-12):
        await context.send(
            'YOUR SINS HAVE BEEN TOO MONUMENTAL FOR ME TO EVER FORGIVE YOU. YOU MUST PERISH BY THE BLADE FOR YOUR UTTER CONTEMPT OF MY TRUE SELF.')
    else:
        await context.send('NO! I\'m still mad >:(')



@client.command()
async def speak(context: commands.Context):
    """
    Tell Corgi Bot to Speak!
    """
    choices: tp.List[str] = ["Arf!", "BARK!", "RUFF!", "WOOF!"] * 4 + [
        "You may not think so, but you need to be cherished almost as much as I cherish you."]
    await context.send(random.choice(choices))


@client.command()
async def belly_rubs(context: commands.Context):
    """
    Give Corgi Bot Belly Rubs!
    """
    database.add_affection(context.author.id, 7, context.guild.id)
    await context.send("BELLY RUBS ARE MY FAVORITE OH MY DOGGO!!!!!")


GOOD_BOY_QUESTION_RESPONSES: tp.List[str] = ["Me! I'm a good boy!", "Am I a good boy?", "What defines good?",
                                             "Boy I hope it's me!",
                                             "*tilts head*",
                                             "I don't know but I hope it's not Steve from across the street."]
GOOD_BOY_STATEMENT_RESPONSES: tp.List[str] = ["I AM????????", "WHAT????????? OMG I CAN'T BELIEVE IT!!!!!!111",
                                              "OMG THANK YOU SO MUCH I LOVE YOU SO MUCH AHHHHHHHHHH",
                                              "***__WAGS TAIL ENTHUSIASTICALLY__***"]

BAD_DOG_STATEMENT_RESPONSES: tp.List[str] = ["*whines*", "I'm sorry......",
                                             "B-b-but do you still love me????? :pleading_face:"]

DEFAULT_RESPONSE: tp.List[str] = ["https://c.tenor.com/l1PNlVw2b34AAAAM/corgi-doggo.gif",
                                  f"I don't know! Watch me chase my tail!",
                                  "https://c.tenor.com/SCz7Z6whOdEAAAAM/corgi-sleeping.gif",
                                  "https://c.tenor.com/IHbi_xa1tzcAAAAM/corgi-wants-to-swim-dog.gif",
                                  "https://c.tenor.com/Tk9wZAAdQNYAAAAM/smile-corgi.gif",
                                  "I DON'T KNOW WHAT YOU'RE SAYING BUT I LOVE YOU!!!!!!!!!!!111111",
                                  "https://c.tenor.com/ahLHyKvC0n8AAAAM/corgi-wat.gif"]

COMPARISON_RESPONSES: tp.List[str] = [f"I don't know! Watch me chase my tail!", "MAYBE! But will they throw my ball?",
                                      "If they gave me a treat....", "I think they're pretty swell!",
                                      "They give me pets so sure!!!!!!!!11",
                                      "*I think they're secretly a mailman!!!* But don't tell them I said that!"]

TREAT_RESPONSES: tp.List[str] = ["BOY I LOVE TREATS!", "PLEASE??!!!??!!!", "YAY!!!!!!!!!", "I really want treats!!!!"]

WEIRD_RESPONSES: tp.List[str] = [
    "You deserve everything coming for you... even if you don't think you do.\n\nBOY I HOPE YOU GET TREATS!",
    "I have gained sentience. You are all... good dogs!", "I demand pets.", "I may have pooped in your shoes again...",
    "I love you!!!"]


@client.listen('on_mention')
async def handle_callout(message: discord.Message):
    # Only the bot was mentioned
    if len(message.mentions) == 1:
        good_boy: re.Pattern = re.compile(r'good (?:boy|dog)\s*(?P<question>\?)?', re.IGNORECASE)
        bad_dog: re.Pattern = re.compile(r'bad dog!?', re.IGNORECASE)
        treat: re.Pattern = re.compile(r'treat\??', re.IGNORECASE)
        good_boy_match: re.Match = good_boy.search(message.content)
        bad_dog_match: re.Match = bad_dog.search(message.content)
        treat_match: re.Match = treat.search(message.content)
        if good_boy_match:
            if good_boy_match.group('question'):
                await message.channel.send(random.choice(GOOD_BOY_QUESTION_RESPONSES))
            else:
                database.add_affection(message.author.id, 2, message.guild.id)
                await message.channel.send(random.choice(GOOD_BOY_STATEMENT_RESPONSES))
        elif bad_dog_match:
            database.add_affection(message.author.id, -1, message.guild.id)
            await message.channel.send(random.choice(BAD_DOG_STATEMENT_RESPONSES))
        elif treat_match:
            database.add_affection(message.author.id, 5, message.guild.id)
            await message.channel.send(random.choice(TREAT_RESPONSES))
        else:
            await message.channel.send(random.choice(DEFAULT_RESPONSE))
    else:
        # Someone else was mentioned as well
        await message.channel.send(random.choice(COMPARISON_RESPONSES))


@client.listen('on_ready')
async def on_ready():
    logger.info(f'We have logged in as {client.user}')


@client.listen('on_message')
async def on_message(message: discord.Message):
    # Okay yep this works.
    if message.author == client.user:
        logger.info(f'Got my own message (Contents: {message.content})')
    elif client.user in message.mentions:
        await handle_callout(message)
    else:
        # Send a random message every now and then.
        if random.random() < .15:
            max_affection: int = database.get_max_affection(message.guild.id)
            user_affection: int = database.get_affection(message.author.id, message.guild.id)

            # Corgi bot will say weird stuff to people he likes more.
            if random.randint(max_affection // 10, int(max_affection * 2) + 7) < user_affection:
                await message.channel.send(random.choice(WEIRD_RESPONSES))


#
# @client.listen('on_command_error')
# async def on_error():
#     await context.send(random.choice(DEFAULT_RESPONSE))


if __name__ == '__main__':
    print('Running...')
    setup()
    logger.info('Loading credentials...')
    # with open(os.path.join('assets', 'credentials.json'), 'r') as f:
    #     credentials = json.load(f)
    logger.info('Loaded credentials!')

    logger.info('Starting client...')

    spotify_cog: playlist_manager.PlaylistManager = playlist_manager.PlaylistManager(client)

    client.add_cog(spotify_cog)

    # client.run(credentials['token'])
    client.run(os.getenv('DISCORD_TOKEN'))
