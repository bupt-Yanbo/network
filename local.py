import asyncio
import struct
import logging
import string
import sys
import websockets
import traceback
import os
path = 'data'
files = os.listdir(path)

logging.basicConfig(level=logging.WARNING)  # 设置日志级别
#read和write的大小
rwsize=1024
username=str(sys.argv[1])
password=str(sys.argv[2])
gSendBandWidth = 0
gRecvBandWidth = 0
now_rdata_len = 0
now_wdata_len = 0
write_data_num=0
write_data=[]
write_max=1000
write_loop=0
read_data_num=0
read_data=[]
read_max=1000
read_loop=0


async def localConsole(ws, path):
    global gSendBandWidth
    global gRecvBandWidth
    global now_rdata_len
    global now_wdata_len
    try:
        while True:
            await asyncio.sleep(1)
            print(f'this is {gSendBandWidth} {gRecvBandWidth}')
            msg = await ws.send(f'{gSendBandWidth} {gRecvBandWidth}')
            now_rdata_len = 0
            now_wdata_len = 0
    except websockets.exceptions.ConnectionClosedError as exc:
        # log.error(f'{exc}')
        print(f'{exc}')
    except websockets.exceptions.ConnectionClosedOK as exc:
        logging.error(f'{exc}')
    except Exception:
        logging.error(f'{traceback.format_exc()}')
        exit(1)

async def clacbrandwidth():
    global gSendBandWidth
    global gRecvBandWidth
    global now_rdata_len
    global now_wdata_len
    # gSendBandWidth = 0
    # gRecvBandWidth = 0
    # last_rdata_len = 0
    # last_wdata_len = 0
    while True:
        gSendBandWidth = now_wdata_len# - last_wdata_len
        gRecvBandWidth = now_rdata_len# - last_rdata_len
        # last_wdata_len = now_wdata_len
        # last_rdata_len = now_rdata_len
        # gSendBandWidth=4
        # print(f'接收带宽：{gRecvBrandWidth!r}')
        # print(f'发送带宽：{gSendBrandWidth!r}')
        await asyncio.sleep(1)

async def my_connect(reader, writer):
    global now_rdata_len
    global now_wdata_len
    data1 = await reader.read(rwsize)#tcp1
    addr = writer.get_extra_info('peername')
    logging.info(f"connect from {addr!r}")
    if len(data1) < 3:
        logging.warning("too short!")
        writer.close()
        return
    request = struct.unpack('!BBB', data1[:3])
    #http
    if request[0] == 67  and request[1] == 79 and request[2] == 78:
        logging.info('in http')
        hdata=data1.decode('utf8')
        hdata1=hdata.split('\r\n')
        hdata2=hdata1[1].split(':')
        t=str.maketrans(string.ascii_letters,string.ascii_letters,' ')
        h_url=hdata2[1].translate(t)
        h_port=hdata2[2].translate(t)
        h_len=len(h_url)
        success=b"HTTP/1.0 200 Connection Established\r\n\r\n"
        try:
            reader_remote, writer_remote = await asyncio.open_connection('127.0.0.2', int(sys.argv[4]))
            writer.write(success)#tcp2
            await writer.drain()
            logging.info(f'connect success ！{h_url}')
        except (TimeoutError, ConnectionRefusedError) as _:
            logging.warning(f'connect failed ！{h_url}')
            writer.write(success)
            await writer.drain()
            writer.close()
            return
        writer_remote.write(data1)#rtcp1
        await writer_remote.drain()
        #login
        login_info=username+'+'+password
        login_info=login_info.encode()
        writer_remote.write(login_info)
        await writer_remote.drain()
        data = await reader_remote.read(rwsize)
        request = struct.unpack('!BB', data[:2])
        if request[0]!=5:
            writer_remote.close()
            logging.warning('incorrect password')
            return
    # if request[1]==2:#cookie
    #     pass

        #
        writer_remote.write(data1)#rtcp1
        data = await reader_remote.read(rwsize)
        if data == success:
            logging.info('connection building successfully')
            up_stream = transport(reader, writer_remote, h_url)
            down_stream = transport(reader_remote, writer, h_url)
            await asyncio.gather(up_stream, down_stream)
    else:
        writer.write(b'\x05\x00') #tcp2
        await writer.drain()
        data2 = await reader.read(rwsize)#method1
        request = struct.unpack('!4B', data2[:4])
     #域名
        if request[0] == 5 and request[1] == 1 and request[3] == 3:
            host_len = struct.unpack('!B', data2[4:5])[0]
            host = data2[5:host_len + 5].decode()
            port = struct.unpack('!H', data2[host_len + 5:])[0]
            logging.info(f'len {host_len},host {host}，port {port}')
            try:
                reader_remote, writer_remote = await asyncio.open_connection('127.0.0.2',int(sys.argv[4]))
                writer.write(struct.pack('!5B', 5, 0, 0, 3, host_len) + host.encode() + struct.pack('!H', port))#tmethod2
                await writer.drain()
                logging.info(f'connect success ！{host}')
            except (TimeoutError, ConnectionRefusedError) as _:
                logging.warning(f'connect failed ！{host}')
                writer.write(struct.pack('!5B', 5, 3, 0, 3, host_len) + host.encode() + struct.pack('!H', port))
                await writer.drain()
                writer.close()
                return
            await connect_remote(writer_remote,reader_remote,writer,reader,data2,data1)
        
    #ipv4地址
        if request[0] == 5 and request[1] == 1 and request[3] == 1:
            ip = '.'.join([str(a) for a in struct.unpack('!BBBB', data2[4:8])])
            port = struct.unpack('H', data2[-2:])[0]
            test1=struct.unpack('!BBBB', data2[4:8])
            print(f'ip {ip}，port {port}，yuan{test1}')
            try:
                reader_remote, writer_remote = await asyncio.open_connection('127.0.0.2', int(sys.argv[4]))
                writer.write(struct.pack('!8B', 5, 0, 0, 1, *struct.unpack('!BBBB', data2[4:8])) + struct.pack('!H', port))
                await writer.drain()
                logging.info(f'connect success ！{ip}')
            except (TimeoutError, ConnectionRefusedError) as _:
                logging.warning(f'connect failed ！{ip}，{repr(_)}')
                writer.write(struct.pack('!8B', 5, 3, 0, 1, *struct.unpack('!BBBB', data2[4:8])) + struct.pack('!H', port))
                await writer.drain()
                writer.close()
                return
            await connect_remote(writer_remote,reader_remote,writer,reader,data2,data1)
        
async def connect_remote(writer_remote,reader_remote,writer,reader,data2,data1):
    writer_remote.write(data1)
    print('hello1')
    await writer_remote.drain()
    print('hello2')
    data = await reader_remote.read(rwsize)
    request = struct.unpack('!BB', data[:2])
    if request[0]==5 and request[1] == 0:#tcp successful
        #login in:
        login_info=username+'+'+password
        login_info=login_info.encode()
        writer_remote.write(login_info)
        await writer_remote.drain()
        data = await reader_remote.read(rwsize)
        request = struct.unpack('!BB', data[:2])
        if request[0]!=5:
            writer_remote.close()
            return
    # if request[1]==2:#cookie
    #     pass
    #
        writer_remote.write(data2)
        await writer_remote.drain()
        datat = await reader_remote.read(rwsize)
        host='local'
        up_stream = transport(reader, writer_remote, host)
        down_stream = transport(reader_remote, writer, host)
        await asyncio.gather(up_stream, down_stream)

async def transport(reader, writer, host):
    global now_rdata_len
    global now_wdata_len
    while reader.at_eof:
        try:
            data = await reader.read(rwsize)
            if(read_loop==0):
                read_data.append(data)
                read_data_num=read_data_num+1
                if(read_data_num>read_max):
                    read_data_num=0
                    read_loop=1
                    filename=open(path + '\\' + "read_data1"+".txt","w+",encoding='utf-8')
                    filename.write(read_data)
            else:
                read_data[read_data_num]=data
                read_data_num=read_data_num+1
                if(read_data_num>read_max):
                    read_data_num=0
                    filename=open(path + '\\' + "read_data2"+".txt","w+",encoding='utf-8')
                    filename.write(read_data)
            now_rdata_len+=len(data)
            if not data:
                writer.close()
                break
        except (ConnectionAbortedError, ConnectionResetError) as _:
            writer.close()
            logging.warning(f'{host} quit {repr(_)}')
            break
        try:
            writer.write(data)
            if(write_loop==0):
                write_data.append(data)
                write_data_num=write_data_num+1
                if(write_data_num>write_max):
                    write_data_num=0
                    write_loop=1
                    filename=open(path + '\\' + "write_data1"+".txt","w+",encoding='utf-8')
                    filename.write(write_data)
            else:
                write_data[write_data_num]=data
                write_data_num=write_data_num+1
                if(write_data_num>write_max):
                    write_data_num=0
                    filename=open(path + '\\' + "write_data2"+".txt","w+",encoding='utf-8')
                    filename.write(write_data)
            now_wdata_len+=len(data)
            await writer.drain()
        except (ConnectionAbortedError, ConnectionResetError) as _:
            writer.close()
            logging.warning(f'{host} abnormal quit {repr(_)}')
            break
        logging.info(f'{host} quit')

async def main():
    server = await asyncio.start_server(
    my_connect, '0.0.0.0', int(sys.argv[3]))    
    addr = server.sockets[0].getsockname()
    logging.warning(f'Serving on {addr}')
    logging.info(f'username: {str(sys.argv[1])}  password: {str(sys.argv[2])}')
    # my_connect
    asyncio.create_task(clacbrandwidth())
    ws_server = await websockets.serve(localConsole, '127.0.0.1', int(sys.argv[3])+1)
    asyncio.create_task(clacbrandwidth())
    # asyncio.create_task(clacbrandwidth())
    async with server:
        await server.serve_forever()

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(main()))
loop.run_forever()
