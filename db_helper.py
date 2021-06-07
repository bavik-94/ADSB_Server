import asyncio
import aiosqlite
database = "C:\\Users\\phili\\Documents\\db\\adsb_messages.db"
faa_registry = "C:\\Users\\phili\\Documents\\db\\aircraft_data2.db"


class DBHelper:
    connect_attempts = 0
    valid_db = False
    last_query = None

    @classmethod
    async def query_init_state(cls):
        async with aiosqlite.connect(database) as db:  # build initial state from any transmission < 10 seconds old
            db.row_factory = aiosqlite.Row
            query = """SELECT rowid, * from squitters 
            WHERE replace(parsed_time, 'T', ' ') >= datetime('now', '-10 seconds')
            """
            async with db.execute(query) as cursor:
                db_msg = []
                async for row in cursor:
                    db_msg.append({key: row[key] for key in row.keys()})

                if len(db_msg) == 0:
                    cls.connect_attempts += 1
                    print("Database is out of date -- Check if parser is running -- " + str(
                        cls.connect_attempts) + " attempts made")
                    await asyncio.sleep(2)
                    return None

                print("Connected to database successfully!")
                row_ids = [entry['rowid'] for entry in db_msg]  # record end of last query
                cls.last_query = max(row_ids)
                cls.valid_db = True
                return db_msg

    @classmethod
    async def query_state(cls):  # query database from the end of the last query
        query_by_last = "SELECT rowid, * FROM squitters WHERE rowid >= ?"
        async with aiosqlite.connect(database) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query_by_last, (cls.last_query,)) as cursor:
                db_msg = []
                async for line in cursor:
                    if line[1] is not None:  # need valid hex_ident
                        db_msg.append({key: line[key] for key in line.keys()})

                row_ids = [entry['rowid'] for entry in db_msg]  # record end of last query
                cls.last_query = max(row_ids)
                return db_msg

    @classmethod
    async def type_query(cls, hex_ident):  # returns FAA registry information and icon type for client live map
        async with aiosqlite.connect(faa_registry) as db2:
            db2.row_factory = aiosqlite.Row
            type_search = "SELECT hex_ident,n_number,manufacturer,model,icon_type from info where hex_ident = ?"
            async with db2.execute(type_search, (hex_ident,)) as cursor2:
                async for line in cursor2:
                    return {'n_number': line['n_number'], 'manufacturer': line['manufacturer'],
                            'model': line['model'], 'icon_type': line['icon_type']}
                return {'n_number': None, 'manufacturer': None, 'model': None,
                        'icon_type': '_generic'}  # aircraft is not registered with the FAA

    @classmethod
    async def flight_history(cls, hex_ident):
        async with aiosqlite.connect(database) as db:  # get aircraft that transmitted anything in the last minute
            db.row_factory = aiosqlite.Row
            search = """
                                            SELECT hex_ident,lat,lon,altitude
                                                FROM squitters
                                                WHERE hex_ident = ? AND transmission_type = 3 AND replace(parsed_time, 'T', ' ') >= datetime('now', '-40 minutes')
                            """
            async with db.execute(search, (hex_ident,)) as cursor:
                db_msg = []
                async for line in cursor:
                    db_msg.append({key: line[key] for key in line.keys()})
                if not db_msg:
                    return {'action': 'history', 'hex_ident': None}
                lat = [x['lat'] for x in db_msg]
                lon = [x['lon'] for x in db_msg]
                alt = [x['altitude'] for x in db_msg]
                history = [{'hex_ident': hex_ident, 'lat': lat, 'lon': lon, 'altitude': alt}, {'action': 'history'}]
                return history
