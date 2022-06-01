import calendar
import os
from datetime import datetime
from discord.ext import tasks

from subgrounds.subgrounds import Subgrounds

from ..constants import KLIMA_CARBON_SUBGRAPH
from ..utils import get_discord_client, \
    update_nickname, update_presence, \
    prettify_number

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
SEVEN_DAYS_IN_SECONDS = 604800

# Initialized Discord client
client = get_discord_client()

sg = Subgrounds()

offsets = ["BCT", "MCO2", "UBO", "NBO", "NCT"]
counter = 0


def get_info():
    global counter
    currentOffset = offsets[counter]

    ts = get_current_date_timestamp() - SEVEN_DAYS_IN_SECONDS
    w_total_amount, w_offset_amount = get_retirement_fees(sg,
                                                          ts,
                                                          currentOffset)

    counter += 1
    if counter == len(offsets):
        counter = 0

    return w_total_amount, w_offset_amount, currentOffset


def get_current_date_timestamp():
    date_string = datetime.utcnow().strftime("%d/%m/%Y")
    date = datetime.strptime(date_string, "%d/%m/%Y")
    current_date_timestamp = round(calendar.timegm(date.timetuple()))

    return current_date_timestamp


def get_retirement_fees(sg, timestamp, offset):
    '''
    param `sg`: Initialized subgrounds object
    param `timestamp`: Timestamp used for cutoff date (data created after
    the provided date will be fetched)
    param `offset`: Specific Offset for which amount and fee will be retrieved

    returns:
    `weekly_total_retirement_fee`: Total fee provided from retirements that
     were accumulated after the provided timestamp
    `weekly_offset_retirement_amount`: Total amount provided from retirements
    for specific offset that were accumulated after the provided timestamp
    `weekly_offset_retirement_fee`: Total fee provided from retirements for
    specific offset that were accumulated after the provided timestamp
    '''

    try:
        kbm = sg.load_subgraph(KLIMA_CARBON_SUBGRAPH)

        retirement_df = kbm.Query.dailyKlimaRetirements(
            where=[kbm.DailyKlimaRetirement.timestamp > timestamp]
        )

        retirement_df = sg.query_df(
            [retirement_df.amount,
             retirement_df.feeAmount,
             retirement_df.token])

        if retirement_df.size == 0:
            return 0, 0, 0

        w_total_amount = retirement_df["dailyKlimaRetirements_amount"].sum()

        w_offset_amount = retirement_df.loc[
            retirement_df['dailyKlimaRetirements_token'] == offset,
            'dailyKlimaRetirements_amount'].sum()

        return w_total_amount, w_offset_amount

    except Exception:
        return None, None, None


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))
    if not update_info.is_running():
        update_info.start()


# Loop time set to 2mins
@tasks.loop(seconds=10)
async def update_info():
    total_amount, offset_amount, offset = get_info()

    if total_amount is not None and offset_amount and offset is not None:

        total_text = f'Retired last 7d: {prettify_number(total_amount)}t'
        success = await update_nickname(client, total_text)
        if not success:
            return

        offset_text = f'{offset} retired: {prettify_number(offset_amount)}t'
        success = await update_presence(
            client,
            offset_text,
            type='playing'
        )
        if not success:
            return

client.run(BOT_TOKEN)
