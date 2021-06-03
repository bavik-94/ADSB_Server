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
        async with aiosqlite.connect(database) as db:  # build initial state from any transmission < 60 seconds old
            async with db.execute("SELECT * from activepos") as cursor:
                db_msg = []
                async for row in cursor:
                    db_msg.append(row)

                if len(db_msg) == 0:
                    cls.connect_attempts += 1
                    print("Database is out of date -- Check if parser is running -- " + str(
                        cls.connect_attempts) + " attempts made")
                    await asyncio.sleep(2)
                    return None
                else:
                    print("Connected to database successfully!")
                    cls.last_query = db_msg[-1]['parsed_time'].replace("T", " ")
                    return db_msg

    @classmethod
    async def query_state(cls):  # query database from the end of the last query
        query_by_last = "SELECT *FROM squitters WHERE replace(parsed_time, 'T', ' ') >= ?"
        async with aiosqlite.connect(database) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query_by_last, (cls.last_query,)) as cursor:
                messages = []
                async for line in cursor:
                    if line[1] is not None:  # need valid hex_ident
                        messages.append(line)
                cls.last_query = messages[-1][-1].replace("T", " ")  # mark last time stamp of line block received
                return messages

    @classmethod
    async def type_query(cls, icao):  # returns FAA registry information and icon type for client live map
        async with aiosqlite.connect(faa_registry) as db2:
            db2.row_factory = aiosqlite.Row
            type_search = "SELECT hex_ident,n_number,manufacturer,type,icon_type from info where hex_ident = ?"
            async with db2.execute(type_search, (icao,)) as cursor2:
                async for line in cursor2:
                    return line
                return {'hex_ident': None, 'n_number': None, 'manufacturer': None, 'type': None, 'icon_type': None}
