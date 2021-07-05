import asyncio
import aiosqlite
import argparse
import operator
import time
import sys
from struct import unpack,pack

capacity = 10000000 #桶容量
#Rate = 0  #速率
class TokenBucket:
    '''
        令牌桶算法：出
            令牌出桶速率恒定，当桶中无剩余令牌，则不能取出
    '''
    def __init__(self, rate, capacity):
        '''
            rate:出桶速率
            volume: 最大容积
            current：桶中现有令牌
            times：计时
        '''
        self._rate = rate
        self._capacity = capacity
        self._current_amount = 0
        self._last_consume_time = int(time.time())
        self.tokenSemaphore = asyncio.BoundedSemaphore(1)

    async def consume(self, token_amount):
        #上锁
        await self.tokenSemaphore.acquire()
        # 从上次发送到这次发送，新取出的令牌数量
        increment = (int(time.time()) - self._last_consume_time) * self._rate
        # 桶中当前剩余令牌数量
        self._current_amount = min(increment + self._current_amount, self._capacity)
        print(self._current_amount, increment, token_amount, self._last_consume_time, int(time.time()))
        # 如果需要的令牌超过剩余的令牌，则不能发送数据
        if token_amount > self._current_amount:
            self.tokenSemaphore.release()
            return False
        self._last_consume_time = int(time.time())
        # 可以取出令牌，取出后桶中剩余令牌数量
        self._current_amount -= token_amount
        #解锁
        self.tokenSemaphore.release()
        return True

async def transport(reader, writer, addr, TB):
    while reader.at_eof:
        try:    # 从reader接收外部报文
            data = await reader.read(1000)
            data_len = sys.getsizeof(data)   #数据大小
            if not data:
                writer.close()
                break
        except (ConnectionAbortedError, ConnectionRefusedError) as e:
            writer.close()
            print(f'{addr}异常退出，{repr(e)}')
            break
        
        try:    # 向writer转发报文
            #指令桶
            if TB.consume(data_len):
                writer.write(data)
                await writer.drain()
        except (ConnectionAbortedError, ConnectionRefusedError) as e:
            writer.close()
            print(f'{addr}异常退出，{repr(e)}')
            break
    print(f'{addr}正常退出')

async def handle_echo(reader, writer):
    data = await reader.read(1000) #将信息读至EOF
    message = data.decode()
    usermessage1 = message.split(' ')
    usermessage = tuple(usermessage1)
    flag = 0

    async with aiosqlite.connect('user.db') as db:
        async with db.execute("SELECT username, password, rate FROM user_table") as uap:
            async for u in uap:
                if usermessage[0]==u[0] and usermessage[1]==u[1] and flag==0:
                    Rate = u[2] #速率
                    flag = 1
                    print("认证成功!!!")
                    writer.write(b'\x01')
                    await writer.drain()
                    
    if flag==0:
        writer.close()
        print("认证失败!!!")

    data = await reader.read(50000) #将信息读至EOF
    if data[0] == ord('C'):
        data1 = data.decode()
        httpdata = data1.split(' ')
    # 判断协议的类型(socks5协议或者http协议)
    # socks5协议
    if data[0] == 5:
        # 解读客户端发来的信息包
        peername = writer.get_extra_info('peername')
        print(f"Create TCP connection with {peername!r}")
        header = unpack('!BBBB', data[:4])  # 读取前面四个基本信息 VER/CMD/RSV/ATYP
        # 判断socks版本号和需要实现的功能(本代理服务器只支持socks5协议，且只能实现connect功能)
        if header[0] == 5 and header[1] == 1:
            if header[3] == 1:  #IPv4 X'01'
                ip = '.'.join([str(i) for i in unpack('!BBBB', data[4:8])]) #获取IP地址，IPv4的地址4个字节
                port = unpack('!H', data[8:10])[0]  #获取端口号，2字节
                print(f'ip:{ip}, port{port}')
                try:
                    dsreader, dswriter = await asyncio.open_connection(ip, port)
                    writer.write(b'\x05\x00\x00' + data[3:11])  #将信息重新打包发回给localproxy，告知客户端代理服务器与目标服务器连接成功
                    await writer.drain()
                    print(f'connect success with {ip} and {port}!')
                except (TimeoutError, ConnectionRefusedError) as e:
                    print(f'connect failed with{ip} and {port}!')
                    print(f'{repr(e)}')
                    writer.close()
                    return
                #指令桶
                TB = TokenBucket(Rate, capacity)
                #并发转发数据包
                await asyncio.gather(transport(reader, dswriter, ip, TB), transport(dsreader, writer, ip, TB))
            if header[3] == 3: #域名 X'03'
                Hostlen = unpack('!B', data[4:5])[0] #域名长度
                Host = data[5: Hostlen+5].decode('utf-8') #解析域名
                port = unpack('!H', data[5+Hostlen: Hostlen+7])[0] #获取端口号，2字节
                print(f'Hostlen:{Hostlen}, Host:{Host}, port:{port}')
                try:
                    dsreader, dswriter = await asyncio.open_connection(Host, port)
                    writer.write(b'\x05\x00\x00'+data[3: Hostlen+7])  #将信息重新打包发回给locoalproxy，告知客户端：代理服务器与目标服务器连接成功
                    await writer.drain()
                    print(f'connect success with {Host} and {port} in SOCKS5!')
                except (TimeoutError, ConnectionRefusedError) as e:

                    print(f'connect failed with{Host} and {port} in SOCKS5!')
                    print(f'{repr(e)}')
                    writer.close()
                    return

                #指令桶
                TB = TokenBucket(Rate, capacity)
                #并发转发数据包
                await asyncio.gather(transport(reader, dswriter, Host, TB), transport(dsreader, writer, Host, TB))
    # http协议
    elif httpdata[0] == 'CONNECT': #只处理http的connect包，其余包暂时不处理
        try:
            httpdata1 = httpdata[1].split(':')
            Host = httpdata1[0] # 获取主机地址
            port = httpdata1[1] # 获取端口号
            dsreader, dswriter = await asyncio.open_connection(Host, port)  # 与目的服务器建立连接
            writer.write(b'HTTP/1.1 200 Connection established\r\n\r\n')    # 将应答包发给localproxy，告知客户端：代理服务器与目标服务器连接成功
            await writer.drain()
            print(f'connect success with {Host} and {port} in HTTP!')
        except (TimeoutError, ConnectionRefusedError) as e:
            print(f'connect failed with {Host} and {port} in HTTP!')
            print(f'{repr(e)}')
            writer.close()
            return

        #指令桶
        TB = TokenBucket(Rate, capacity)
        #并发转发数据包
        await asyncio.gather(transport(reader, dswriter, Host, TB), transport(dsreader, writer, Host, TB))
    else:
        print("we can't handle this type of request")
        writer.close()
        return


async def main():

    async with aiosqlite.connect('user.db') as db:
        #await db.execute("DROP TABLE user_table") #删除表
        await db.execute("CREATE TABLE if not exists user_table ( username VARCHAR(50) primary key, password VARCHAR(50), rate INT)")
        #await db.execute("DELETE FROM user_table")#删除表中的数据
        #await db.execute("INSERT INTO user_table ( username, password) VALUES ('R52125', 'R100214')")
        #await db.execute("INSERT INTO user_table ( username, password) VALUES ('F444627549', 'XJBRCBR')")
        
        await db.execute("DELETE FROM user_table where username = 1")
        await db.execute("INSERT INTO user_table (username, password, rate) VALUES (?, ?, ?)" ,(args.username, args.password, args.rate))
        await db.execute("DELETE FROM user_table where username = 1")
        await db.commit()

        async with db.execute("SELECT username, password, rate FROM user_table") as uap:
            async for u in uap:
                print(f'f1={u[0]} f2={u[1]} f3={u[2]}')
    
    server = await asyncio.start_server(handle_echo, '127.0.0.5', 1085)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--username", help="please input the username you want to add, but it can't be '1'.", default=1)
parser.add_argument("-p", "--password", help="please input the password you want to add, but it can't be '1'.", default=1)
#parser.add_argument("-pp", "--ppassword", help="please define the password again")
parser.add_argument("-r", "--rate", help="please input rate", default=0)
args = parser.parse_args()

asyncio.run(main())
