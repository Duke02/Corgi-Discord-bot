import discord
import os.path
import json
import logging
import typing as tp
import random
import datetime
import quotes
import re
from discord.ext import commands

import relationship

PREFIX: str = '$'
client: commands.Bot = commands.Bot(command_prefix=PREFIX)

logger: logging.Logger = logging.getLogger('discord')


def setup():
    logging_filename: str = os.path.join('logs', f'{datetime.datetime.utcnow():%Y%m%d_%H%M%S%f}.log')

    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename=logging_filename, encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s|%(name)s]: %(message)s'))
    logger.addHandler(handler)


setup()

quotes_manager: quotes.QuotesDatabase = quotes.QuotesDatabase()
affection_manager: relationship.RelationshipDatabase = relationship.RelationshipDatabase()


@client.command()
async def roll(context: commands.Context, die: str) -> tp.List[int]:
    d_index: int = die.find('d')
    num_dice: int = int(die[:d_index])
    num_faces: int = int(die[d_index + 1:])

    rolls: tp.List[int] = [random.randint(1, num_faces) for _ in range(num_dice)]
    await context.send(f'You rolled a {sum(rolls)}! (Individual rolls: {", ".join([str(r) for r in rolls])})')


@client.group()
async def quote(context: commands.Context):
    if context.invoked_subcommand is None:
        await _quote_get(context)


@quote.command(name='get')
async def _quote_get(context: commands.Context):
    quote_got = quotes_manager.get_random_quote()
    await context.send(quote_got)


@quote.command(name='store')
async def _quote_store(context: commands.Context, actual_quote: str, author: tp.Optional[str]):
    time = datetime.datetime.now().timestamp()
    quotes_manager.add_quote(actual_quote, author, time)
    await context.send(
        f'Stored quote!\nTime: {datetime.datetime.fromtimestamp(time):%B %d, %Y %H:%M:%S}, Author: {author}, Quote: {actual_quote}')


@client.command()
async def ping(context: commands.Context):
    sent_time = context.message.created_at
    current_time = datetime.datetime.now()

    await context.send(
        f'I BROUGHT THE BALL BACK IN {(current_time - sent_time).microseconds / 1e3}MS! DO I GET A TREAT?')


@client.command()
async def ball(context: commands.Context):
    affection_manager.add_affection(context.message.author.id, 1)
    await ping(context)


@client.command()
async def hello(context: commands.Context):
    await context.send(f'Hello there {context.message.author.mention}!!! Will you give me pets?????')


@client.command()
async def pet(context: commands.Context, n_pets: int = 1):
    affection_manager.add_affection(context.message.author.id, 3 * n_pets)
    await context.send(f'I LOVE PETS SO MUCH BUT NOT AS MUCH AS I LOVE YOU!!!!!!!!!!!')


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
        good_boy: re.Pattern = re.compile(r'good (?:boy|dog)\s*(?P<question>\?)?')
        bad_dog: re.Pattern = re.compile(r'bad dog!?')
        treat: re.Pattern = re.compile(r'treat\??')
        good_boy_match: re.Match = good_boy.search(message.content)
        bad_dog_match: re.Match = bad_dog.search(message.content)
        treat_match: re.Match = treat.search(message.content)
        if good_boy_match:
            if good_boy_match.group('question'):
                await message.channel.send(random.choice(GOOD_BOY_QUESTION_RESPONSES))
            else:
                affection_manager.add_affection(message.author.id, 2)
                await message.channel.send(random.choice(GOOD_BOY_STATEMENT_RESPONSES))
        elif bad_dog_match:
            affection_manager.add_affection(message.author.id, -1)
            await message.channel.send(random.choice(BAD_DOG_STATEMENT_RESPONSES))
        elif treat_match:
            affection_manager.add_affection(message.author.id, 5)
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
        if random.random() < .02:
            await message.channel.send(random.choice(WEIRD_RESPONSES))
            return

#
# @client.listen('on_command_error')
# async def on_error():
#     await context.send(random.choice(DEFAULT_RESPONSE))


if __name__ == '__main__':
    print('Running...')
    setup()
    logger.info('Loading credentials...')
    with open(os.path.join('assets', 'credentials.json'), 'r') as f:
        credentials = json.load(f)
    logger.info('Loaded credentials!')

    logger.info('Starting client...')
    client.run(credentials['token'])