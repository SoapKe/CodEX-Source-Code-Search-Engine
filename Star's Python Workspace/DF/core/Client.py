# coding=utf-8
# author:Star
import socket
import json
import hashlib
from LogWriter import LogWriter


class Client:
    __sk_client = ''
    __main_server_ip = ''
    __main_server_port = ''

    def __init__(self, main_server_ip, main_server_port):
        self.__main_server_ip = main_server_ip
        self.__main_server_port = main_server_port
        self.__sk_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect_main_server(self):
        try:
            self.__sk_client.connect((self.__main_server_ip, self.__main_server_port))
        except:
            LogWriter().write_error_log("Cannot connect to main server!")

    def send_message(self, message={}):
        print("in")
        to_send = json.dumps(message).encode("utf-8")
        m = hashlib.md5()
        m.update(to_send)
        digest = m.hexdigest()
        header = json.dumps({'message_size': len(to_send), 'fingerprint': digest}).encode('utf-8')
        print(header)
        try:
            self.__sk_client.send(header)
            self.__sk_client.send('\n'.encode('utf-8'))
            while len(to_send) > 1024:
                trunk = to_send[0:1024]
                to_send = to_send[1024:]
                self.__sk_client.send(trunk)
            if len(to_send) > 0:
                self.__sk_client.send(to_send)

        except:
            LogWriter().write_error_log("Message {} is not sent to main server!".format(header))


if __name__ == '__main__':
    c = Client("localhost", 9609)
    c.connect_main_server()
    i = 0
    s = 'a'
    while i<10:
        s+='Star '
        i+=1
    msg = {'start':s}
    print(msg)
    c.send_message(msg)
