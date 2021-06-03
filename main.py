import argparse
import asyncio
import json
import logging
import sys
import time
import os
from tabulate import tabulate

import websockets
from db_helper import DBHelper as Db
from aircraft import Aircraft as Ac


debug = False
time_start = int(time.time())
USERS = set()


async def init_state():
    while Db.connect_attempts < 10:  # connect to database and check if data is fresh
        result = await Db.query_init_state()
        if result:
            for entry in result:
                await Ac.new_aircraft(entry)
            return
    print("\nDatabase has invalid data after 10 attempts... closing")
    sys.exit()


async def state_update():
    global debug
    while Db.valid_db:
        messages = await Db.query_state()
        for entry in messages:
            _aircraft = await Ac.get_aircraft(entry['hex_ident'])
            if _aircraft:  # existing aircraft
                await _aircraft.update(entry)
            else:
                await Ac.new_aircraft(entry)

# clean up aircraft that haven't transmitted in 1 minute
Ac.expired = [aircraft for aircraft in Ac.active if await aircraft.expired_check()]
Ac.active = [aircraft for aircraft in Ac.active if aircraft not in Ac.expired]

# send state - only non expired and with valid lat lon alt
if USERS:
    message = [await x.get_values() for x in Ac.active if x.lon != 0]
    message.append({'type': 'state'})
    await asyncio.wait([user.send(json.dumps(message)) for user in USERS])

# print state to console
if debug:
    os.system('cls')
    active, expired = await Ac.tables()
    print("\nTime Elapsed: " + time.strftime("%H:%M:%S", time.gmtime(int(time.time() - time_start))))
    print("\nActive Aircraft: " + str(len(active)))
    print(tabulate(active, headers=active[0].keys()))
    print("\nExpired Aircraft: " + str(len(expired)))
    print(tabulate(expired, headers=expired[0].keys()))

await asyncio.sleep(2)


async def register(websocket):
    USERS.add(websocket)
    return


async def unregister(websocket):
    USERS.remove(websocket)
    return


async def server(websocket, path):
    await register(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "history":
                #  get flight history
                pass
            else:
                logging.error("unsupported event: %s", data)
    finally:
        await unregister(websocket)

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", default=debug, help="Prints a table of the currently tracked aircraft")
args = parser.parse_args()
debug = args.debug

start_server = websockets.serve(server, "localhost", 6789)

asyncio.get_event_loop().run_until_complete(init_state())
asyncio.get_event_loop().create_task(state_update())
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
