import time
from db_helper import DBHelper as Db

from aircraft import Aircraft as Ac


class Flights:
    active = []
    expired = []

    @classmethod
    async def get_aircraft(cls, hex_ident):
        for aircraft in cls.active:
            if aircraft.hex_ident == hex_ident:
                return aircraft
        return None

    @classmethod
    async def new_aircraft(cls, db_data):
        type_info = await Db.type_query(db_data['hex_ident'])
        n_aircraft = Ac(int(time.time()), **db_data, **type_info)
        cls.active.append(n_aircraft)

    @classmethod
    async def tables(cls):
        active_table = [await aircraft.get_values() for aircraft in cls.active]
        expired_table = [await aircraft.get_values() for aircraft in cls.expired]
        return active_table, expired_table

