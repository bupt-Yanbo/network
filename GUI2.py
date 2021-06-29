from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebSockets import *
import sys
import os
import humanfriendly

class Window(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setGeometry(700,50,500,550)
        self.setWindowTitle('网络管理器')
        # self.resize(350,100)
        self.username='zyb'
        self.remoteport=7900
        self.localport=7777
        self.lim_flag = '否'
        self.startBtn = QPushButton('连接',self)
        self.startBtn.clicked.connect(self.startClicked)
        self.startBtn.move(20,290)

        self.lb1 = QLabel('主机端口：',self)
        self.lb1.move(20,20)

        self.lb2 = QLabel('本地端口：',self)
        self.lb2.move(20,80)

        self.lb3 = QLabel('用户名：',self)
        self.lb3.move(20,140)

        self.lb4 = QLabel('密码：',self)
        self.lb4.move(20,200)

        self.lb11 = QLabel('是否限速：', self)
        self.lb11.move(20, 260)

        self.bt1 = QPushButton('修改主机端口',self)
        self.bt1.move(200,20)

        self.bt2 = QPushButton('修改本地端口',self)
        self.bt2.move(200,80)        

        self.bt3 = QPushButton('切换用户',self)
        self.bt3.move(200,140)

        self.bt5 = QPushButton('更改限速设置', self)
        self.bt5.move(200, 255)

        # self.bt4 = QPushButton('密码',self)
        # self.bt4.move(200,200)        

        self.lb6 = QLabel('7900',self)
        self.lb6.move(80,20)

        self.lb7 = QLabel('7777',self)
        self.lb7.move(80,80)

        self.lb8 = QLabel('zyb',self)
        self.lb8.move(80,140)

        self.lb12 = QLabel('否', self)
        self.lb12.move(90, 260)

        self.edit = QLineEdit(self)
        self.edit.installEventFilter(self)

        #怎么布局在布局篇介绍过，这里代码省略...

        self.edit.setContextMenuPolicy(Qt.NoContextMenu)
        self.edit.setPlaceholderText("密码6-15位，只能有数字和字母")
        self.edit.move(68,197)
        self.edit.setFixedSize(300,20)
        self.edit.setEchoMode(QLineEdit.Password)

        regx = QRegExp("^[0-9A-Za-z]{14}$")
        validator = QRegExpValidator(regx, self.edit)
        self.edit.setValidator(validator)

        self.sendBandwidthLabel = QLabel(self)
        self.sendBandwidthLabel.setText('  发送带宽：')
        self.sendBandwidthLabel.resize(450,30)
        self.sendBandwidthLabel.move(20,330)
        self.sendBandwidthLabel.setStyleSheet("color: rgb(0, 0, 0);background-color: white")

        self.recvBandwidthLabel = QLabel(self)
        self.recvBandwidthLabel.setText('  接收带宽：')
        self.recvBandwidthLabel.resize(450,30)
        self.recvBandwidthLabel.move(20,360)
        self.recvBandwidthLabel.setStyleSheet("color: rgb(0, 0, 0);background-color: white")
        # self.lb9 = QLabel('******',self)
        # self.lb9.move(120,200)

        self.bt1.clicked.connect(self.showDialog)
        self.bt2.clicked.connect(self.showDialog)
        self.bt3.clicked.connect(self.showDialog)
        self.bt5.clicked.connect(self.showDialog)
        # self.bt4.clicked.connect(self.showDialog2)
        
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.finished.connect(self.processFinished)
        self.process.started.connect(self.processStarted)
        self.process.readyReadStandardOutput.connect(self.processReadyRead)
    
    def showDialog(self):
        sender = self.sender()
        if sender == self.bt1:
            text, ok = QInputDialog.getInt(self, '修改主机端口', '请输入主机端口：',min=7780,max=8000)
            if ok:
                self.lb6.setText(str(text))
                self.remoteport=text 
        elif sender == self.bt2:
            text, ok = QInputDialog.getInt(self, '修改本地端口', '请输入本地端口：', min = 7000,max=7779) 
            if ok:
                self.lb7.setText(str(text))
                self.localport=text
        elif sender == self.bt3:
            text, ok = QInputDialog.getText(self, '切换用户', '请输入用户名')            
            if ok:
                self.lb8.setText(text)      
                self.username=text
        elif sender == self.bt5:
            if self.lim_flag == '否':
                self.lim_flag = '是'
            else:
                self.lim_flag = '否'
            self.lb12.setText(self.lim_flag)

    def processReadyRead(self):
        data = self.process.readAll()
        try:
            msg = data.data().decode().strip()
            # log.debug(f'msg={msg}')
        except Exception as exc:
            # log.error(f'{traceback.format_exc()}')
            exit(1)
        
    def processStarted(self):
        # print("p start")
        process = self.sender() # 此处等同于 self.process 只不过使用sender适应性更好
        processId = process.processId()
        # log.debug(f'pid={processId}')
        self.startBtn.setText('Stop')
        # self.processIdLine.setText(str(processId))

        self.websocket = QWebSocket()
        self.websocket.connected.connect(self.websocketConnected)
        self.websocket.disconnected.connect(self.websocketDisconnected)
        try:
            self.websocket.textMessageReceived.connect(self.websocketMsgRcvd)
            self.websocket.open(QUrl(f'ws://127.0.0.1:{int(self.localport)+1}'))
            print("connect")
        except:
            print("disconnect")
        
    def processFinished(self):
        self.process.kill()

    def startClicked(self):
        btn = self.sender()
        # print("so?")
        text = btn.text().lower()
        if text.startswith('连接'):
            # listenPort = self.listenPortLine.text()
            # username = self.usernameLine.text()
            username = self.username
            remoteport = self.remoteport
            localport=self.localport
            password = self.edit.text()
            print(username,password,remoteport,localport)
            # consolePort = self.consolePortLine.text()
            # remoteHost = self.remoteHostLine.text()
            # remotePort = self.remotePortLine.text()
            # pythonExec = os.path.basename(sys.executable)
            # 从localgui启动localproxy直接使用-w 提供用户密码，不再使用命令行交互输入，因为有些许问题
            # cmdLine = f'{pythonExec} work6.py local -p {listenPort} -u {username} -w {password} -k {consolePort} {remoteHost} {remotePort}'
            # cmdLine="D:\v2py\.vscode\pydwork1\m6\local.py zyb 135800"
            cmdLine=f'python .vscode\pydwork1\m6\pyqtwebsocket\localtest.py {username} {password} {localport} {remoteport}'
            # .vscode\pydwork1\m6\finalv1\local.py
            # .vscode\pydwork1\m6\pyqtwebsocket\localtest.py
            # log.debug(f'cmd={cmdLine}')
            # print("now")
            self.process.start(cmdLine)
            # print("so")
        else:
            self.process.kill()
            self.startBtn.setText('连接')

    def websocketConnected(self):
        self.websocket.sendTextMessage('secret')

    def websocketDisconnected(self):
        self.process.kill()

    def websocketMsgRcvd(self, msg):
        # log.debug(f'msg={msg}')
        # print("here sockets")
        sendBandwidth, recvBandwidth, *_ = msg.split()
        nowTime = QDateTime.currentDateTime().toString('hh:mm:ss')
        print(f'{nowTime} {humanfriendly.format_size(int(sendBandwidth))}')
        self.sendBandwidthLabel.setText(f'  发送带宽：  {nowTime} {humanfriendly.format_size(int(sendBandwidth))}')
        # print("something")
        # print(f'{nowTime} {humanfriendly.format_size(int(sendBandwidth))}')
        self.recvBandwidthLabel.setText(f'  接收带宽：  {nowTime} {humanfriendly.format_size(int(recvBandwidth))}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Window()
    ex.show()
    sys.exit(app.exec_())