import asyncio
import struct
import logging
import string
import sqlite3
import aiosqlite3
import time
import sys
import  socket


logging.basicConfig(level=logging.WARNING)  # 设置日志级别
#read和write的大小
rwsize=1024
CapacityTimes=1
ratetimes=2000
global lockall
checktime=1
lockall=asyncio.Lock()
fast_connect=1
if_find_ip=0
async def main1():
    async with aiosqlite3.connect("user.db") as db:
        if len(sys.argv)==1:
            print("清除数据,并新建表")
            await db.execute("DROP TABLE IF EXISTS list")
            await db.commit()
        else:
            print("新建表")   
        await db.execute('''CREATE TABLE list
        (name VARCHAR(30) PRIMARY KEY     NOT NULL,
        passwd         TEXT    NOT NULL,
        bps            INT     NOT NULL,
        current_amount DOUBLE  NOT NULL,
        last_time      DOUBLE  NOT NULL
        );''')
        await db.execute("INSERT INTO list (name,passwd,bps,current_amount,last_time) \
        VALUES ('zyb','135800',2000,0,0)")

        await db.commit()

async def fast_connection():
    async with aiosqlite3.connect("user1.db") as db:
        if len(sys.argv)==1:
            print("清除数据,并新建表")
            await db.execute("DROP TABLE IF EXISTS FAST_CONNECTION")
            await db.commit()
        else:
            print("新建表")
        await db.execute('''CREATE TABLE FAST_CONNECTION
        (name VARCHAR(30) PRIMARY KEY     NOT NULL,
        ip         TEXT    NOT NULL,
        fluence            INT     NOT NULL
       
        );''')

        await db.commit()

async def check_name(host):
    # print("进入加速系统")
    global if_find_ip
    async with aiosqlite3.connect("user1.db") as db:
        await db.execute(f'update FAST_CONNECTION set fluence=fluence-1 where name="{host}"')
        await db.execute(f'delete from FAST_CONNECTION where fluence<0')
        await db.commit()
        async with db.execute(f'SELECT fluence from FAST_CONNECTION where name="{host}"') as cursor:
            if len(list(cursor)) > 0:
                is_exist = 1
            else:
                is_exist = 0
        if is_exist == 1:
            async with db.execute(f'SELECT fluence,ip  from FAST_CONNECTION where name="{host}"') as cursor:
                for row in cursor:
                    fluence = row[0]
                    the_ip = row[1]
                    if_find_ip = 1
                    logging.info(f'fluence:', fluence)
            await db.execute(f'update FAST_CONNECTION set fluence={fluence+2} where name="{host}"')
            await db.commit()
            db.close()
            return
        else:
            myaddr = socket.getaddrinfo(host, 'http')
            # print(myaddr[0][4][0])
            if len(myaddr[0][4][0])<20:
                await db.execute(f'INSERT INTO FAST_CONNECTION (name,ip,fluence) \
                    VALUES ("{host}","{myaddr[0][4][0]}",20)')
                await db.commit()


        db.close()
        if_find_ip=0
        return


async def my_connect(reader, writer):
    global lockall
    BaseRate=1000
    BaseCapacity=BaseRate*CapacityTimes
    data = await reader.read(rwsize)
    addr = writer.get_extra_info('peername')
    logging.info(f"connect from {addr!r}")
    if len(data) < 3:
        logging.warning("too short!")
        writer.close()
        return
    request = struct.unpack('!BBB', data[:3])
    if request[0] == 67  and request[1] == 79 and request[2] == 78:
        #identify
        login_info=await reader.read(rwsize)
        request =login_info.decode('utf8')
        id_info=request.split('+')
        logging.info(f'received request: username: {id_info[0]} ,password : {id_info[1]}')
        #查数据库
        result=await checkID(id_info[0],id_info[1])
        if result>0:
            logging.info("legal user")
            checktime=result/10
            logging.info(f'get bps {BaseRate},capacity {BaseCapacity}')
            writer.write(b'\x05\x01')
            await writer.drain()
        else:
            writer.write(b'\x01\x01')
            writer.close()
            logging.info("illegal user")
            return     
        data = await reader.read(rwsize)
        hdata=data.decode('utf8')
        hdata1=hdata.split('\r\n')
        hdata2=hdata1[1].split(':')
        t=str.maketrans(string.ascii_letters,string.ascii_letters,' ')
        h_url=hdata2[1].translate(t)
        h_port=hdata2[2].translate(t)
        h_len=len(h_url)
        success=b"HTTP/1.0 200 Connection Established\r\n\r\n"
        try:
            reader_remote, writer_remote = await asyncio.open_connection(h_url, h_port)
            writer.write(success)
            await writer.drain()
            logging.info(f'connect success ！{h_url}')
        except (TimeoutError, ConnectionRefusedError) as _:
            logging.warning(f'connect failed ！{h_url}')
            writer.write(success)
            await writer.drain()
            writer.close()
            return
        # lock1=lockall
        lock1=asyncio.Lock()
        limit = TokenBucket(BaseRate,BaseCapacity,id_info[0],lock1)#设置获得令牌的速度，令牌桶上限
        up_stream = transport(reader, writer_remote, h_url,limit,checktime)
        down_stream = transport(reader_remote, writer, h_url,limit,checktime)
        await asyncio.gather(up_stream, down_stream)
    else:   
        writer.write(b'\x05\x00')
        await writer.drain()
        #identity
        login_info=data = await reader.read(rwsize)
        request =login_info.decode('utf8')
        id_info=request.split('+')
        logging.info(f'received request: username: {id_info[0]} ,password : {id_info[1]}')
        #查数据库
        BaseRate=1000
        # BaseCapacity=10*BaseRate
        result=await checkID(id_info[0],id_info[1])
        if result>0:
            logging.info("legal user")
            checktime=result/10
            logging.info(f'get bps {BaseRate},capacity {BaseCapacity}')
            writer.write(b'\x05\x01')
            await writer.drain()
        else:
            writer.write(b'\x01\x01')
            logging.info("illegal user")
            writer.close()
            return       

        data = await reader.read(rwsize)
        request = struct.unpack('!4B', data[:4])
        # print(data)

            #域名
        if request[0] == 5 and request[1] == 1 and request[3] == 3:
            host_len = struct.unpack('!B', data[4:5])[0]
            host = data[5:host_len + 5].decode()
            # 快速连接
            if fast_connect==1:
                pass
                # print("判断是否加速")
                await check_name(host)

            if if_find_ip==0:
                # print("未加速")
                port = struct.unpack('!H', data[host_len + 5:])[0]
                logging.info(f'len {host_len},host {host}，port {port}')
                try:
                    reader_remote, writer_remote = await asyncio.open_connection(host, port)
                    writer.write(struct.pack('!5B', 5, 0, 0, 3, host_len) + host.encode() + struct.pack('!H', port))
                    await writer.drain()
                    logging.info(f'connect success ！{host}')
                except (TimeoutError, ConnectionRefusedError) as _:
                    logging.warning(f'connect failed ！{host}')
                    writer.write(struct.pack('!5B', 5, 3, 0, 3, host_len) + host.encode() + struct.pack('!H', port))
                    await writer.drain()
                    writer.close()
                    return
            # lock1=lockall
                lock1=asyncio.Lock()
                limit = TokenBucket(BaseRate,BaseCapacity,id_info[0],lock1)#设置获得令牌的速度，令牌桶上限
                up_stream = transport(reader, writer_remote, host,limit,checktime)
                down_stream = transport(reader_remote, writer, host,limit,checktime)
                await asyncio.gather(up_stream, down_stream)
            else:
                # 加速系统
                logging.info(f'speed up!')
                print("speed up")

        #ipv4地址
        if request[0] == 5 and request[1] == 1 and request[3] == 1:
            ip = '.'.join([str(a) for a in struct.unpack('!BBBB', data[4:8])])
            port = struct.unpack('H', data[-2:])[0]
            test1=struct.unpack('!BBBB', data[4:8])
            # print(f'ip {ip}，port {port}，yuan{test1}')
            try:
                reader_remote, writer_remote = await asyncio.open_connection('127.0.0.2', 7778)
                writer.write(struct.pack('!8B', 5, 0, 0, 1, *struct.unpack('!BBBB', data[4:8])) + struct.pack('!H', port))
                await writer.drain()
                logging.info(f'connect success ！{ip}')
            except (TimeoutError, ConnectionRefusedError) as _:
                logging.warning(f'connect failed ！{ip}，{repr(_)}')
                writer.write(struct.pack('!8B', 5, 3, 0, 1, *struct.unpack('!BBBB', data[4:8])) + struct.pack('!H', port))
                await writer.drain()
                writer.close()
                return
            # lock1=lockall
            lock1=asyncio.Lock()
            limit = TokenBucket(BaseRate,BaseCapacity,id_info[0],lock1)#设置获得令牌的速度，令牌桶上限
            up_stream = transport(reader, writer_remote, ip,limit,checktime)
            down_stream = transport(reader_remote, writer, ip,limit,checktime)
            await asyncio.gather(up_stream, down_stream)    

async def transport(reader, writer, host,limit,checktime):
    ltime=0
    while reader.at_eof:
        # print("want token")
        if ltime>checktime:
            ltime=0
            # await limit.consume(rwsize/8)#获得令牌则继续
        ltime=ltime+1
        # print('got token')
        try:
            data = await reader.read(rwsize)
            if not data:
                writer.close()
                break
        except (ConnectionAbortedError, ConnectionResetError) as _:
            writer.close()
            logging.warning(f'{host} quit {repr(_)}')
            break
        try:
            writer.write(data)
            await writer.drain()
        except (ConnectionAbortedError, ConnectionResetError) as _:
            writer.close()
            logging.warning(f'{host} abnormal quit {repr(_)}')
            break
        logging.info(f'{host} quit')    

async def checkID(username,passwd):
    lpasswd="1111"
    async with aiosqlite3.connect("user.db") as db:
        async with db.execute(f'SELECT passwd  from list where name="{username}"') as cursor:
            if len(list(cursor))>0:
                is_exist=1
            else:
                is_exist=0
                passwd='0000'
        if is_exist==1:
            async with db.execute(f'SELECT passwd,bps  from list where name="{username}"') as cursor:
                for row in cursor:
                    lpasswd=row[0]
                    Rate=row[1]
                    logging.info(f'passwd:',lpasswd)
                    logging.info(f'bps:',Rate)
    db.close()
    if lpasswd==passwd:
        return Rate
    else:
        return -1


class TokenBucket:
 
    # rate是令牌发放速度，capacity是桶的大小
    def __init__(self, rate, capacity,username,lock):
        self._rate = rate
        self._capacity = capacity
        self.username=username
        self.lock=lock
        self._current_amount=0
        self._last_consume_time=0
    # token_amount是发送数据需要的令牌数
    async def consume(self, token_amount):
        flag=1
        async with aiosqlite3.connect("user.db") as db:
            async with db.execute(f'SELECT current_amount,last_time  from list where name="{self.username}"') as cursor:
                for row in cursor:
                    self._current_amount=row[0]
                    self._last_consume_time=row[1]
                    logging.info(f'current_amount:',row[0])
                    logging.info(f'last_time:',row[1])
        while flag==1:
            # await self.lock.acquire()
            increment = (time.time() - self._last_consume_time) * self._rate  # 计算从上次发送到这次发送，新发放的令牌数量
            logging.info(f'increment {increment}')
            # print("increment ",increment)
            self._current_amount = min(
                increment + self._current_amount, self._capacity)  # 令牌数量不能超过桶的容量
            # await self.lock.acquire()
            if self._current_amount>token_amount:
                # print("check")
                await self.lock.acquire()
                flag=0
                self._last_consume_time = time.time()
                self._current_amount -= token_amount
                async with aiosqlite3.connect("user.db") as db:
                    await db.execute(f'update list set current_amount={self._current_amount} where name="{self.username}"')
                    await db.execute(f'update list set last_time={self._last_consume_time} where name="{self.username}"')
                    await db.commit()
                self.lock.release()

async def main():
    await main1()
    await fast_connection()
    server = await asyncio.start_server(
    my_connect, '127.0.0.2', 7900)

    addr = server.sockets[0].getsockname()
    logging.warning(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(main()))
loop.run_forever()
