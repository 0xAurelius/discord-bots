import os
import traceback

import discord
from discord.ext import commands
import json
from web3 import Web3

from .constants import KLIMA_PROTOCOL_SUBGRAPH, POLYGON_DIGITAL_CARBON_SUBGRAPH, \
                       AVG_BLOCK_SECS, DISTRIBUTOR_ADDRESS

PROVIDER_POLYGON_URL = os.environ['WEB3_PROVIDER_POLYGON_URL']
PROVIDER_ETH_URL = os.environ['WEB3_PROVIDER_ETH_URL']
PROVIDER_BASE_URL = os.environ['WEB3_PROVIDER_BASE_URL']


def get_polygon_web3():
    web3 = Web3(Web3.HTTPProvider(PROVIDER_POLYGON_URL))

    assert web3.is_connected()

    return web3


def get_eth_web3():
    web3_eth = Web3(Web3.HTTPProvider(PROVIDER_ETH_URL))

    assert web3_eth.is_connected()

    return web3_eth


def get_base_web3():
    web3_base = Web3(Web3.HTTPProvider(PROVIDER_BASE_URL))

    assert web3_base.is_connected()

    return web3_base


def get_discord_client(members_intent=False, presences_intent=False, message_content_intent=False):
    intents = discord.Intents.default()
    intents.members = members_intent
    intents.presences = presences_intent
    intents.message_content = message_content_intent

    client = commands.Bot(intents=intents, help_command=None, command_prefix='&?')

    return client


def load_abi(filename):
    '''Load a single ABI from the `abis` folder under `src`'''
    script_dir = os.path.dirname(__file__)
    abi_dir = os.path.join(script_dir, 'abis')

    with open(os.path.join(abi_dir, filename), 'r') as f:
        abi = json.loads(f.read())

    return abi


async def update_nickname(client, nickname_text):
    for guild in client.guilds:
        guser = guild.get_member(client.user.id)
        try:
            await guser.edit(nick=nickname_text)
        except discord.errors.HTTPException:
            return False

    return True


async def update_presence(client, text, type='watching'):
    if type == 'watching':
        type = discord.ActivityType.watching
    elif type == 'playing':
        type = discord.ActivityType.playing
    else:
        raise ValueError(
            'Invalid value for type passed to update_presence! '
            'Must be either "watching" or "playing"'
        )

    try:
        await client.change_presence(
            activity=discord.Activity(
                type=type,
                name=text
            )
        )
        return True
    except discord.errors.HTTPException:
        return False


def get_last_metric(sg):
    kpm = sg.load_subgraph(KLIMA_PROTOCOL_SUBGRAPH)

    last_metric = kpm.Query.protocolMetrics(
        orderBy=kpm.ProtocolMetric.timestamp,
        orderDirection='desc',
        first=1
    )

    return last_metric


def get_last_carbon(sg):
    kpm = sg.load_subgraph(POLYGON_DIGITAL_CARBON_SUBGRAPH)

    last_carbon = kpm.Query.epoches(
        orderBy=kpm.Epoch.epoch, orderDirection='desc', first=1
    )

    return last_carbon


def prettify_number(number):
    num = float('{:.3g}'.format(number))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


def get_staking_params(web3):
    distributor_contract = web3.eth.contract(
        address=DISTRIBUTOR_ADDRESS,
        abi=load_abi('distributor.json')
    )

    try:
        epoch_length = distributor_contract.functions.epochLength().call()

        info = distributor_contract.functions.info(0).call()
        reward_rate = info[0]
        staking_reward = distributor_contract.functions.nextRewardAt(reward_rate).call()

        return staking_reward, epoch_length
    except ValueError:
        traceback.print_exc()
        return None


def get_rebases_per_day(blocks_per_rebase):
    '''
    Calculates the average number of rebases per day based on the average
    block production time for the previous 1 million blocks
    '''

    secs_per_rebase = blocks_per_rebase * AVG_BLOCK_SECS

    return 24 / (secs_per_rebase / 60 / 60)
