import argparse
import asyncio
import websockets
import logging
import time
from struct import unpack,pack
import os
path = 'data'
files = os.listdir(path)

SendBand = 0
RecvBand = 0
SendBandwidth = 0
RecvBandwidth = 0

write_data=[]
write_max=1000
write_loop=0
read_data_num=0
read_data=[]
read_max=1000
read_loop=0

async def localConsole(ws, path):
    global SendBandwidth
    global RecvBandwidth
    try:
        while True:
            await asyncio.sleep(1)
            msg = await ws.send(f'{int(SendBandwidth)} {int(RecvBandwidth)}')
    except websockets.exceptions.ConnectionClosedError as exc:
        logging.error(f'{exc}')
    except websockets.exceptions.ConnectionClosedOK as exc:
        logging.error(f'{exc}')
    except Exception:
        # logging.error(f'{traceback.format_exc()}')
        exit(1)

async def transport(reader, writer, addr):
    global SendBand
    global RecvBand
    while reader.at_eof:
        try:    # 从reader接收外部报文
            data = await reader.read(1000)
            if (read_loop == 0):
                read_data.append(data)
                read_data_num = read_data_num + 1
                if (read_data_num > read_max):
                    read_data_num = 0
                    read_loop = 1
                    filename = open(path + '\\' + "read_data1" + ".txt", "w+", encoding='utf-8')
                    filename.write(read_data)
            else:
                read_data[read_data_num] = data
                read_data_num = read_data_num + 1
                if (read_data_num > read_max):
                    read_data_num = 0
                    filename = open(path + '\\' + "read_data2" + ".txt", "w+", encoding='utf-8')
                    filename.write(read_data)
            RecvBand += len(data)
            if not data:
                writer.close()
                break
        except (ConnectionAbortedError, ConnectionRefusedError) as e:
            writer.close()
            print(f'{addr}异常退出，{repr(e)}')
            break
        try:    # 向writer转发报文
            SendBand += len(data)
            writer.write(data)
            if (write_loop == 0):
                write_data.append(data)
                write_data_num = write_data_num + 1
                if (write_data_num > write_max):
                    write_data_num = 0
                    write_loop = 1
                    filename = open(path + '\\' + "write_data1" + ".txt", "w+", encoding='utf-8')
                    filename.write(write_data)
            else:
                write_data[write_data_num] = data
                write_data_num = write_data_num + 1
                if (write_data_num > write_max):
                    write_data_num = 0
                    filename = open(path + '\\' + "write_data2" + ".txt", "w+", encoding='utf-8')
                    filename.write(write_data)
            await writer.drain()
        except (ConnectionAbortedError, ConnectionRefusedError) as e:
            writer.close()
            print(f'{addr}异常退出，{repr(e)}')
            break
    print(f'{addr}正常退出')

async def count_width():
    global SendBand
    global RecvBand
    global SendBandwidth
    global RecvBandwidth
    time.sleep(1)
    SendBandwidth = SendBand/1
    SendBand = 0
    print('SendBandwidth:', SendBandwidth)
    RecvBandwidth = RecvBand/1
    RecvBand = 0
    print('RecvBandwidth:', RecvBandwidth)

async def handle_echo(reader, writer):
    data = await reader.read(5000) #将第一个信息读至EOF
    data1 = data.decode()
    httpdata = data1.split(' ')
    # 客户端发送的协商版本和认证方法请求长度不小于3B
    if len(data) < 3:
        print('VER and CMD of is error')
        print('connecte failed')
        return

    a = (args.username, args.password)
    usermas = ' '.join(a).encode()

    # 判断协议的类型(socks5协议或者http协议)
    # socks5协议
    if data[0] == 5:
        # 解读客户端发来的第一个信息包
        peername = writer.get_extra_info('peername')
        print(f"Create TCP connection with {peername!r}")
        # 向客户端回复版本号5(支持socks5)，并告知采用无验证需求(CMD='00')
        writer.write(b"\x05\x00")
        await writer.drain()    # 等待客户端发送请求
        # 客户端发送请求细节，服务器接收
        data = await reader.read(1024)  #将第二个信息读至EOF
        header = unpack('!BBBB', data[:4])  # 读取前面四个基本信息 VER/CMD/RSV/ATYP
        # 判断socks版本号和需要实现的功能(本代理服务器只支持socks5协议，且只能实现connect功能)
        if header[0] == 5 and header[1] == 1:
            if header[3] == 1:  #IPv4 X'01'
                try:
                    dsreader, dswriter = await asyncio.open_connection('127.0.0.5', 1085)   #向远端代理发起连接请求

                    dswriter.write(usermas)
                    await writer.drain()
                    VER = await dsreader.read(50000)
                    if VER[0] != 1:
                        writer.close()

                    dswriter.write(data)   #将数据包发给remoteproxy
                    await dswriter.drain()
                    REP = await dsreader.read(1024) #从远端代理处接收应答包
                    writer.write(REP)   #将应答包转发给客户端
                    await writer.drain()
                    print(f'connect success with 127.0.0.5 and 1085 !')
                except (TimeoutError, ConnectionRefusedError) as e:
                    print(f'connect failed with 127.0.0.5 and 1085 !')
                    print(f'{repr(e)}')
                    writer.close()
                    return
                #并发转发数据包
                await asyncio.gather(transport(reader, dswriter, '127.0.0.1'), transport(dsreader, writer, '127.0.0.1'), count_width())
            if header[3] == 3: #域名 X'03'
                try:
                    dsreader, dswriter = await asyncio.open_connection('127.0.0.5', 1085)

                    dswriter.write(usermas)
                    await writer.drain()
                    VER = await dsreader.read(50000)
                    if VER[0] != 1:
                        writer.close()

                    dswriter.write(data)   #将数据包发给remoteproxy
                    await dswriter.drain()
                    REP = await dsreader.read(1024) #从远端代理处接收应答包
                    writer.write(REP)   #将应答包转发给客户端
                    await writer.drain()

                    print(f'connect success with 127.0.0.5 and 1085 in SOCKS5!')
                except (TimeoutError, ConnectionRefusedError) as e:
                    print(f'connect failed with 127.0.0.5 and 1085 in SOCKS5!')
                    print(f'{repr(e)}')
                    writer.close()
                    return
                #并发转发数据包
                await asyncio.gather(transport(reader, dswriter, '127.0.0.5'), transport(dsreader, writer, '127.0.0.5'), count_width())
    # http协议
    elif httpdata[0] == 'CONNECT': #只处理http的connect包，其余包暂时不处理
        try:
            dsreader, dswriter = await asyncio.open_connection('127.0.0.5', 1085)  # 与remoteproxy建立连接

            #账号、密码认证
            dswriter.write(usermas)
            await dswriter.drain()

            VER = await dsreader.read(50000)
            if VER[0] != 1:
                writer.close()

            dswriter.write(data)   #将数据包发给remoteproxy
            await dswriter.drain()
            REP = await dsreader.read(1024) #从远端代理处接收应答包
            writer.write(REP)    #将应答包转发给客户端
            await writer.drain()
            print(f'connect success with 127.0.0.5 and 1085 in HTTP!')
        except (TimeoutError, ConnectionRefusedError) as e:
            print(f'connect failed with 127.0.0.1 and 1085 in HTTP!')
            print(f'{repr(e)}')
            writer.close()

            return
        await asyncio.gather(transport(reader, dswriter, '127.0.0.5'), transport(dsreader, writer, '127.0.0.5'), count_width())
    else:
        print("we can't handle this type of request")
        writer.close()
        return


async def main():
    print(args.username, args.password)
    if args.consolePort:
        ws_server = await websockets.serve(localConsole, '127.0.0.1', args.consolePort)
        logging.info(f'CONSOLE LISTEN {ws_server.sockets[0].getsockname()}')
    
    #asyncio.create_task(calcBandwidth())

    server_1 = await asyncio.start_server(handle_echo, '127.0.0.1', 1080)
    #print('1')

    addr = server_1.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server_1:
        await server_1.serve_forever()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="please input your username")
    parser.add_argument("-p", "--password", help="please input your password")
    parser.add_argument("-c", "--consolePort", help="please input the consolePort", default=0 )
    args = parser.parse_args()

    asyncio.run(main())
