import mimetypes
import json
import logging
import urllib.parse
import socket
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

BASE_DIR = Path()
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000


class MyFramework(BaseHTTPRequestHandler):

    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        print(route.query)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('message.html')
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)

    def do_POST(self):
        size = self.headers.get('Content-Length')
        data = self.rfile.read(int(size))

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data,(SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header(keyword='Location',value='/message')
        self.end_headers()


    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type, *_ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header('Content-Type', mime_type)
        else:
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

def save_data_from_form(data):
    filename = 'storage/data.json'
    timestamp = datetime.now().isoformat()
    parse_data = urllib.parse.unquote_plus(data.decode())
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data_dict = json.load(f)
    except FileNotFoundError:
        data_dict = {}
    try:
        parse_dict = {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}
        data_dict[timestamp] = parse_dict
        with open(filename, 'w',encoding='utf-8') as file:
            json.dump(data_dict, file, ensure_ascii= False, indent= 4)
    except ValueError as e:
        logging.error(e)
    except OSError as e:
        logging.error(e)

def run_socket_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host,port))
    logging.info('Socket server started ...')
    try:
        while True:
            msg, address = server_socket.recvfrom(BUFFER_SIZE)
            save_data_from_form(msg)
    except KeyboardInterrupt:
        pass
    finally:
        server_socket.server_close()

def run_http_server(host, port):
    address = (host, port)
    http_server = HTTPServer(address, MyFramework)
    logging.info('HTTP server started ...')
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http_server.server_close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')

    server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    server.start()

    server_socket = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    server_socket.start()