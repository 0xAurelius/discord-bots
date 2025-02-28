import os

from discord.ext import tasks

from ..contract_info import aero_weth_usdc_price, token_supply, uni_v2_pool_price
from ..constants import MANIC_ADDRESS, MANIC_DECIMALS, MANIC_WETH_POOL_ADDRESS
from ..utils import get_discord_client, \
    get_base_web3, load_abi, \
    prettify_number, update_nickname, update_presence

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

# Initialized Discord client
client = get_discord_client()

# Initialize web3
web3 = get_base_web3()

manic_abi = load_abi('erc20_token.json')


def get_info():
    weth_usdc_price = 1 / aero_weth_usdc_price()
    manic_weth_price = 1 / (uni_v2_pool_price(web3, MANIC_WETH_POOL_ADDRESS, MANIC_DECIMALS) / 10**18)
    supply = token_supply(web3, MANIC_ADDRESS, manic_abi, MANIC_DECIMALS)

    return manic_weth_price * weth_usdc_price, supply


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))
    if not update_info.is_running():
        update_info.start()


@tasks.loop(seconds=300)
async def update_info():
    price, supply = get_info()

    if price is not None and supply is not None:
        mcap = price*supply
        mcap_prettified = prettify_number(mcap)

        success = await update_nickname(client, f'MCap: ${mcap_prettified}')
        if not success:
            return

        success = await update_presence(client, f'MANIC Price: ${price:,.4f}')
        if not success:
            return


client.run(BOT_TOKEN)
