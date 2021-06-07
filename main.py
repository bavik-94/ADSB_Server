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
from flights import Flights as Flt

debug = False
time_start = int(time.time())
USERS = set()


async def init_state():
    while Db.connect_attempts < 10:  # connect to database and check if data is fresh
        messages = await Db.query_init_state()
        if messages:
            for entry in messages:
                _aircraft = await Flt.get_aircraft(entry['hex_ident'])
                if _aircraft:  # existing aircraft
                    await _aircraft.update(entry)
                else:
                    await Flt.new_aircraft(entry)

            return
    print("\nDatabase has invalid data after 10 attempts... closing")
    sys.exit()


async def state_update():
    global debug
    while Db.valid_db:
        messages = await Db.query_state()
        for entry in messages:
            _aircraft = await Flt.get_aircraft(entry['hex_ident'])
            if _aircraft:  # existing aircraft
                await _aircraft.update(entry)
            else:
                await Flt.new_aircraft(entry)

        # clean up aircraft that haven't transmitted in 1 minute

        for aircraft in Flt.active:
            if await aircraft.expired_check():
                Flt.expired.append(aircraft)

        Flt.active = [aircraft for aircraft in Flt.active if aircraft not in Flt.expired]
        Flt.expired = [aircraft for aircraft in Flt.expired if time.time() - aircraft.live <= 270]

        # send state - only non expired and with valid lat lon alt
        if USERS:
            message = [await x.get_values() for x in Flt.active if x.lon != '']
            message.append({'action': 'state'})
            await asyncio.wait([user.send(json.dumps(message)) for user in USERS])

        # print state to console
        if debug:
            os.system('cls')
            active, expired = await Flt.tables()
            print("\nTime Elapsed: " + time.strftime("%H:%M:%S", time.gmtime(int(time.time() - time_start))))
            print("\nActive Aircraft: " + str(len(active)))
            if active:
                print(tabulate(active, headers={key: key for key in active[0].keys()}))
            print("\nExpired Aircraft: " + str(len(expired)))
            if expired:
                print(tabulate(expired, headers={key: key for key in expired[0].keys()}))

        await asyncio.sleep(2)


async def get_flight_history(websocket, hex_ident):
    await websocket.send(json.dumps(await Db.flight_history(hex_ident)))

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
            if data["action"] == "history":
                print(data)
                await get_flight_history(websocket, data['hex_ident'])

            else:
                logging.error("unsupported event: %s", data)
    finally:
        await unregister(websocket)

parser = argparse.ArgumentParser()
parser.add_argument("--debug", default=debug, help="Prints a table of the currently tracked aircraft", action="store_true")
args = parser.parse_args()
debug = args.debug

start_server = websockets.serve(server, "192.168.0.24", 6789)

asyncio.get_event_loop().run_until_complete(init_state())
asyncio.get_event_loop().create_task(state_update())
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
