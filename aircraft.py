from db_helper import DBHelper as Db
from math import sin, cos, sqrt, atan2, radians
import time


class Aircraft:

    active = []
    expired = []

    def __init__(self, live, **kwargs):
        self.hex_ident = kwargs['hex_ident']
        self.n_number = kwargs['n_number']
        self.manufacturer = kwargs['manufacturer']
        self.type = None
        self.call = None
        self.lat = kwargs['lat']
        self.lon = kwargs['lon']
        self.alt = kwargs['altitude']
        self.gs = 0
        self.roc = 0
        self.hdg = 0
        self.live = live
        self.msgs = 0
        self.icon_type = 'generic_'
        self.first_seen = live

    async def update(self, message):
        for key, value in message.items():
            setattr(self, key, value)
        self.live = int(time.time())
        self.msgs += 1
        return

    async def expired_check(self):
        if int(time.time()) - self.live >= 60:
            return True
        return False

    async def get_values(self):
        if await self.expired_check():
            return {'hex_ident': self.hex_ident, 'msgs': self.msgs, 'alive': self.live - self.first_seen,
                    'distance': await Aircraft.get_distance(self.lat, self.lon)}
        return self.__dict__

    @classmethod
    async def get_aircraft(cls, icao):
        for aircraft in cls.active:
            if aircraft.icao == icao:
                return aircraft
        return None

    @classmethod
    async def new_aircraft(cls, db_data):
        type_info = await Db.type_query(['hex_ident'])
        n_aircraft = cls(int(time.time()), **db_data, **type_info)
        cls.active.append(n_aircraft)

    @classmethod
    async def tables(cls):
        active_table = [aircraft.get_values() for aircraft in cls.active]
        expired_table = [aircraft.get_values() for aircraft in cls.expired]
        return active_table, expired_table

    @classmethod
    async def get_distance(cls, lat, lon):  # returns distance in miles from antenna
        if lat == 0:
            return None
        r = 6373.0

        lat1 = radians(40.60747684862169)
        lon1 = radians(-74.27305810697905)
        lat2 = radians(lat)
        lon2 = radians(lon)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance_mi = (r*c) / 1.609344  # r*c = distance in km, divide by 1.609344 to get miles
        return distance_mi
