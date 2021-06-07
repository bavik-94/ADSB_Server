from math import sin, cos, sqrt, atan2, radians
import time


class Aircraft:

    def __init__(self, live, **kwargs):
        self.hex_ident = kwargs['hex_ident']
        self.reg = kwargs['n_number']
        self.mfr = kwargs['manufacturer']
        self.model = kwargs['model']
        self.callsign = kwargs['hex_ident']
        self.lat = kwargs['lat']
        self.lon = kwargs['lon']
        self.altitude = kwargs['altitude']
        self.ground_speed = 0
        self.vertical_rate = 0
        self.track = 0
        self.live = live
        self.msgs = 0
        self.icon_type = kwargs['icon_type']
        self.first_seen = live

    async def update(self, db_data):
        for key, value in db_data.items():
            if key not in ('rowid', 'transmission_type', 'parsed_time'):
                if value != '':
                    setattr(self, key, value)

        self.live = int(time.time())
        self.msgs += 1
        return

    async def expired_check(self):
        if int(time.time()) - self.live >= 60:
            return True
        return False

    async def get_values(self):  # todo check valid lat lon before calc distance
        if await self.expired_check():
            return {'hex_ident': self.hex_ident, 'msgs': self.msgs, 'alive': self.live - self.first_seen,
                    'distance': await Aircraft.get_distance(self.lat, self.lon)}
        return self.__dict__

    @classmethod
    async def get_distance(cls, lat, lon):  # returns distance in miles from antenna
        if lat == 0 or type(lat) != float:
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

        distance_mi = (r * c) / 1.609344  # r*c = distance in km, divide by 1.609344 to get miles
        return distance_mi

