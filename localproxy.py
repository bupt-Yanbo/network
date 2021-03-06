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

write_data_num=0
write_data=[]
write_max=0
write_loop=0

read_data_num=0
read_data=[]
read_max=0
read_loop=0

data11=''
data22=''

async def localConsole(ws, path):
    global SendBandwidth
    global RecvBandwidth
    try:
        while True:
            await asyncio.sleep(1)
            # print('SendBandwidth, RecvBandwidth ', SendBandwidth, ' ', RecvBandwidth)
            msg = await ws.send(f'{int(SendBandwidth)} {int(RecvBandwidth)}')
            SendBandwidth = 0
            RecvBandwidth = 0
    except websockets.exceptions.ConnectionClosedError as exc:
        logging.error(f'{exc}')
    except websockets.exceptions.ConnectionClosedOK as exc:
        logging.error(f'{exc}')
    except Exception:
        # logging.error(f'{traceback.format_exc()}')
        exit(1)

async def readfile():
    global read_data,read_loop,read_data_num,data11
    # print(data11)
    if data11 != '':
        # print('read_loop:', read_loop)
        if (read_loop == 0):
            read_data.append(data11)
            read_data_num = read_data_num + 1
            # print('read_data_num, read_max:', read_data_num, read_max)
            if (read_data_num > read_max):
                read_data_num = 0
                read_loop = 1

                read_data1 = ''.join('%s' %a for a in read_data)
                filename = open(path + '\\' + "read_data1" + ".txt", "a+", encoding='utf-8')
                # filename = open("read_data1.txt", "a+")
                filename.write(read_data1 + "\n")
                filename.close()

        else:
            read_data[read_data_num] = data11
            read_data_num = read_data_num + 1
            if (read_data_num > read_max):
                read_data_num = 0
                read_data1 = ''.join('%s' %a for a in read_data)
                filename = open(path + '\\' + "read_data2" + ".txt", "a+", encoding='utf-8')
                # filename = open("read_data2.txt", "a+")
                filename.write(read_data1 + "\n")
                filename.close()
    data11 = ''

async def writefile():
    global write_data, write_loop,write_data_num,data22
    if data22 != '':
        if (write_loop == 0):
            write_data.append(data22)
            write_data_num = write_data_num + 1
            if (write_data_num > write_max):
                write_data_num = 0
                write_loop = 1

                write_data1 = ''.join('%s' %a for a in write_data)
                filename = open(path + '\\' + "write_data1" + ".txt", "a+", encoding='utf-8')
                # filename = open("write_data1.txt", "a+")
                filename.write(write_data1 + "\n")
                filename.close()
        else:
            write_data[write_data_num] = data22
            write_data_num = write_data_num + 1
            if (write_data_num > write_max):
                write_data_num = 0

                write_data1 = ''.join('%s' %a for a in write_data)
                filename = open(path + '\\' + "write_data2" + ".txt", "a+", encoding='utf-8')
                # filename = open("write_data2.txt", "a+")
                filename.write(write_data1 + "\n")
                filename.close()
    data22 = ''

async def transport(reader, writer, addr):
    global SendBand
    global RecvBand
    global data11, data22
    while reader.at_eof:
        try:    # ???reader??????????????????
            data = await reader.read(1000)
            RecvBand += len(data)

            data11 = data

            if not data:
                writer.close()
                break
        except (ConnectionAbortedError, ConnectionRefusedError) as e:
            writer.close()
            print(f'{addr}???????????????{repr(e)}')
            break
        try:    # ???writer????????????
            SendBand += len(data)
            writer.write(data)
            await writer.drain()

            data22 = data
            # asyncio.run(writefile(data))

        except (ConnectionAbortedError, ConnectionRefusedError) as e:
            writer.close()
            print(f'{addr}???????????????{repr(e)}')
            break
    print(f'{addr}????????????')

async def count_width():
    global SendBand
    global RecvBand
    global SendBandwidth
    global RecvBandwidth
    time.sleep(1)
    SendBandwidth = SendBand/1
    SendBand = 0
    # print('SendBandwidth, SendBand: ', SendBand, ' ', SendBandwidth)
    print('SendBandwidth:', SendBandwidth)
    RecvBandwidth = RecvBand/1
    RecvBand = 0
    print('RecvBandwidth:', RecvBandwidth)

async def handle_echo(reader, writer):
    data = await reader.read(5000) #????????????????????????EOF
    data1 = data.decode()
    httpdata = data1.split(' ')
    # ??????????????????????????????????????????????????????????????????3B
    if len(data) < 3:
        print('VER and CMD of is error')
        print('connecte failed')
        return

    a = (args.username, args.password)
    usermas = ' '.join(a).encode()

    # ?????????????????????(socks5????????????http??????)
    # socks5??????
    if data[0] == 5:
        # ??????????????????????????????????????????
        peername = writer.get_extra_info('peername')
        print(f"Create TCP connection with {peername!r}")
        # ???????????????????????????5(??????socks5)?????????????????????????????????(CMD='00')
        writer.write(b"\x05\x00")
        await writer.drain()    # ???????????????????????????
        # ?????????????????????????????????????????????
        data = await reader.read(1024)  #????????????????????????EOF
        header = unpack('!BBBB', data[:4])  # ?????????????????????????????? VER/CMD/RSV/ATYP
        # ??????socks?????????????????????????????????(???????????????????????????socks5????????????????????????connect??????)
        if header[0] == 5 and header[1] == 1:
            if header[3] == 1:  #IPv4 X'01'
                try:
                    dsreader, dswriter = await asyncio.open_connection('127.0.0.5', 1085)   #?????????????????????????????????

                    dswriter.write(usermas)
                    await writer.drain()
                    VER = await dsreader.read(50000)
                    if VER[0] != 1:
                        writer.close()

                    dswriter.write(data)   #??????????????????remoteproxy
                    await dswriter.drain()
                    REP = await dsreader.read(1024) #?????????????????????????????????
                    writer.write(REP)   #??????????????????????????????
                    await writer.drain()
                    print(f'connect success with 127.0.0.5 and 1085 !')
                except (TimeoutError, ConnectionRefusedError) as e:
                    print(f'connect failed with 127.0.0.5 and 1085 !')
                    print(f'{repr(e)}')
                    writer.close()
                    return
                #?????????????????????
                await asyncio.gather(transport(reader, dswriter, '127.0.0.1'), transport(dsreader, writer, '127.0.0.1'), count_width(), readfile(), writefile())
            if header[3] == 3: #?????? X'03'
                try:
                    dsreader, dswriter = await asyncio.open_connection('127.0.0.5', 1085)

                    dswriter.write(usermas)
                    await writer.drain()
                    VER = await dsreader.read(50000)
                    if VER[0] != 1:
                        writer.close()

                    dswriter.write(data)   #??????????????????remoteproxy
                    await dswriter.drain()
                    REP = await dsreader.read(1024) #?????????????????????????????????
                    writer.write(REP)   #??????????????????????????????
                    await writer.drain()

                    print(f'connect success with 127.0.0.5 and 1085 in SOCKS5!')
                except (TimeoutError, ConnectionRefusedError) as e:
                    print(f'connect failed with 127.0.0.5 and 1085 in SOCKS5!')
                    print(f'{repr(e)}')
                    writer.close()
                    return
                #?????????????????????
                await asyncio.gather(transport(reader, dswriter, '127.0.0.5'), transport(dsreader, writer, '127.0.0.5'), count_width(), readfile(), writefile())
    # http??????
    elif httpdata[0] == 'CONNECT': #?????????http???connect??????????????????????????????
        try:
            dsreader, dswriter = await asyncio.open_connection('127.0.0.5', 1085)  # ???remoteproxy????????????

            #?????????????????????
            dswriter.write(usermas)
            await dswriter.drain()

            VER = await dsreader.read(50000)
            if VER[0] != 1:
                writer.close()

            dswriter.write(data)   #??????????????????remoteproxy
            await dswriter.drain()
            REP = await dsreader.read(1024) #?????????????????????????????????
            writer.write(REP)    #??????????????????????????????
            await writer.drain()
            print(f'connect success with 127.0.0.5 and 1085 in HTTP!')
        except (TimeoutError, ConnectionRefusedError) as e:
            print(f'connect failed with 127.0.0.1 and 1085 in HTTP!')
            print(f'{repr(e)}')
            writer.close()

            return
        await asyncio.gather(transport(reader, dswriter, '127.0.0.5'), transport(dsreader, writer, '127.0.0.5'), count_width(), readfile(), writefile())
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
