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
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * from activepos") as cursor:
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
                async with db.execute("SELECT rowid FROM squitters ORDER BY ROWID DESC LIMIT 1") as cursor2:
                    async for row in cursor2:
                        cls.last_query = row['rowid']
                cls.valid_db = True
                return db_msg

    @classmethod
    async def query_state(cls):  # query database from the end of the last query
        query_by_last = "SELECT * FROM squitters WHERE rowid >= ?"
        async with aiosqlite.connect(database) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query_by_last, (cls.last_query,)) as cursor:
                messages = []
                async for line in cursor:
                    if line[1] is not None:  # need valid hex_ident
                        messages.append(line)
                async with db.execute("SELECT rowid FROM squitters ORDER BY ROWID DESC LIMIT 1") as cursor2:
                    async for row in cursor2:
                        cls.last_query = row['rowid']  # mark last time stamp of line block received
                return messages

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
