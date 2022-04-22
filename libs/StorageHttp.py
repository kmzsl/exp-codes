import socket
import selectors
import re
import json
import sys
import os
import time as t
from loguru import logger

logger.add("/tmp/storage.log", format="{time} {level} {message}",
        level="DEBUG", rotation="100 MB", compression="zip")

class HttpHeaders():

    def __init__(self):
        pass

    def set_property(self, name, value):

        if isinstance(value, str):
            if re.match(r"^\d+$", value):
                setattr(self, name, int(value))
            else:
                setattr(self, name, value)
        else:
            setattr(self, name, value)


class StorageHttp:

    def __init__(self):
        self.settings = "/etc/storage.conf"
        self.messages_json = "/etc/messages.json"
        self._get_settings()
        self._start_server()

    def accept_http_request(self, server_socket):

        self._time_request()
        client, addr = server_socket.accept()

        if self._can_process_client_request():
            self.selector.register(
                fileobj=client, events=selectors.EVENT_READ, data=self._recv)
        else:
            logger.info(f"Too Many Requests, droped {addr}")
            http_answer = self._http_answers("many")
            client.send(http_answer.encode())
            client.close()

    def set_property(self, name, value):

        if isinstance(value, str):
            if re.match(r"^\d+$", value):
                setattr(self, name, int(value))
            else:
                setattr(self, name, value)
        else:
            setattr(self, name, value)

    def event_loop(self):

        while True:
            events = self.selector.select()
            for key, _, in events:
                callback = key.data
                callback(key.fileobj)

    def post(self, client_socket, headers):

        read_bytes = headers.contentlength
        http_body = client_socket.recv(read_bytes)
        data_from_json = json.loads(http_body.decode())
        key, value = data_from_json["key"], json.dumps(data_from_json["value"])

        if self.storage.exists(key):
            logger.info(f"[{headers.remoteaddr}] key = {key} exists")
            http_answer = self._http_answers("exists")
            client_socket.send(http_answer.encode())
        else:
            self.storage.add(key, value)
            logger.info(f"[{headers.remoteaddr}] key = {key} added")
            http_answer = self._http_answers("add")
            client_socket.send(http_answer.encode())

    def put(self, client_socket, path, headers):

        read_bytes = headers.contentlength
        http_body = client_socket.recv(read_bytes)
        data_from_json = json.loads(http_body.decode())
        key, value = path, json.dumps(data_from_json["value"])

        if self.storage.exists(key):
            self.storage.update(key, value)
            logger.info(f"[{headers.remoteaddr}] key = {key} updated")
            http_answer = self._http_answers("update")
            client_socket.send(http_answer.encode())
        else:
            logger.info(f"[{headers.remoteaddr}] key = {key} not found")
            http_answer = self._http_answers("notfound")
            client_socket.send(http_answer.encode())

    def get(self, client_socket, key, headers):

        if self.storage.exists(key):
            json_message = self.storage.get(key)
            json_message_length = len(json_message)
            http_answer = f"HTTP/1.1 200 OK\nContent-Type: application/json\nContent-Length:  {json_message_length}\n\n{json_message}\n"

            client_socket.send(http_answer.encode())
        else:
            logger.info(f"[{headers.remoteaddr}] key = {key} not found")
            http_answer = self._http_answers("notfound")
            client_socket.send(http_answer.encode())

    def delete(self, client_socket, key, headers):

        if self.storage.exists(key):
            self.storage.delete(key)
            logger.info(f"[{headers.remoteaddr}] key = {key} deleted")
            http_answer = self._http_answers("delete")
            client_socket.send(http_answer.encode())
        else:
            logger.info(f"[{headers.remoteaddr}] key = {key} not found")
            http_answer = self._http_answers("notfound")
            client_socket.send(http_answer.encode())

    def _start_server(self):

        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.server_host, self.server_port))
            self.server.listen()
        except socket.error as msg:
            print(f"Can`t create socket: {msg}")
            sys.exit()

        self.selector = selectors.DefaultSelector()
        self.selector.register(
            fileobj=self.server,
            events=selectors.EVENT_READ,
            data=self.accept_http_request
        )

    def _get_settings(self):

        path = os.path.abspath(os.path.dirname(sys.argv[0]))
        config_size = os.path.getsize(path + self.settings)

        if config_size == 0:
            print("Config file is empty")
            sys.exit()

        with open(path + self.settings, "r") as config:
            for line in config:
                try:
                    key, value = line.split()
                    if not hasattr(self, key):
                        if re.match(r"^\d+$", value):
                            setattr(self, key, int(value))
                        else:
                            setattr(self, key, value)
                except ValueError:
                    print(f"Error load {self.settings}: config error")
                    sys.exit()

        with open(path + self.messages_json, "r") as json_f:
            if not hasattr(self, 'http_messages'):
                try:
                    setattr(self, 'http_messages', json.loads(json_f.read()))
                except json.decoder.JSONDecodeError:
                    print(f"Error load {self.messages_json}: not json")
                    sys.exit()

        self._check_settings()

    def _check_settings(self):

        options = [
            'server_host', 'server_port', 'server_bytes_recv',
            'server_max_clients', 'server_base_root'
        ]

        for option in options:
            if not hasattr(self, option):
                print(f"Error: {option} not init")
                sys.exit()

    def _recv(self, client_socket):

        try:

            headers = HttpHeaders()
            headers.set_property("remoteaddr", client_socket.getpeername()[0])
            self._read_http_headers(client_socket, headers)
            self._execute_http_method(client_socket, headers)

        except json.decoder.JSONDecodeError:

            logger.error(f"[{headers.remoteaddr}] Json decode error")
            http_answer = self._http_answers("jsondecode")
            client_socket.send(http_answer.encode())

        except KeyError:

            logger.error(f"[{headers.remoteaddr}] Json format error")
            http_answer = self._http_answers("jsonerror")
            client_socket.send(http_answer.encode())

        except (ValueError, AttributeError):

            logger.error(f"[{headers.remoteaddr}] bad request")
            http_answer = self._http_answers("badhttp")
            client_socket.send(http_answer.encode())

        except OSError:

            logger.debug("connection abort")

        finally:

            self.selector.unregister(client_socket)
            client_socket.close()

    def _get_http_method(self, method):

        return getattr(self, method)

    def _read_http_headers(self, client_socket, headers):

        read_socket = True
        http_header = ""
        request_data = []

        while read_socket:
            chunk = client_socket.recv(self.server_bytes_recv)
            if len(chunk) == 0:
                read_socket = False

            if chunk != b"\r" and chunk != b"\n":
                http_header += chunk.decode()

            if chunk == b"\n":
                request_data.append(http_header)
                http_header = ""
                endpart = client_socket.recv(2)

                if endpart == b"\r\n":
                    read_socket = False
                else:
                    http_header += endpart.decode()

        self._make_http_headers(request_data, headers)

    def _make_http_headers(self, request_data, headers):

        if len(request_data) == 0:
            raise ValueError

        http_method, http_path, _ = request_data[0].split(" ")
        headers.set_property("method", http_method.lower())
        headers.set_property("uri", http_path)

        for header in request_data[1:]:
            parse_header = re.search(r"^([^:]+)\s*:\s*(.+)$", header)
            header_name = re.sub("-", "", parse_header.group(1).lower())
            header_value = parse_header.group(2)
            headers.set_property(header_name, header_value)

    def _execute_http_method(self, client_socket, headers):

        uri_params = [param for param in headers.uri.split("/") if param]

        if len(uri_params) == 0:
            uri_params.append(self.server_base_root)

        if headers.method == "post":
            if uri_params[0] == self.server_base_root:
                http_method = self._get_http_method(headers.method)
                http_method(client_socket, headers)
            else:
                logger.info(f"[{headers.remoteaddr}] [{headers.uri}] Not Found")
                http_answer = self._http_answers("notfound")
                client_socket.send(http_answer.encode())

        elif headers.method in ["get", "put", "delete"]:
            if uri_params[0] == self.server_base_root:
                if len(uri_params) > 1:
                    http_method = self._get_http_method(headers.method)
                    http_method(client_socket, uri_params[1], headers)
                else:
                    logger.info(f"[{headers.remoteaddr}] [{headers.uri}] forgot enter a key")
                    http_answer = self._http_answers("nokey")
                    client_socket.send(http_answer.encode())
            else:
                logger.info(f"[{headers.remoteaddr}] [{headers.uri}] Not Found")
                http_answer = self._http_answers("notfound")
                client_socket.send(http_answer.encode())
        else:
            logger.info(f"[{headers.remoteaddr}] [{headers.method}] Method Not Allowed")
            http_answer = self._http_answers("notallowed")
            client_socket.send(http_answer.encode())

    def _time_request(self):

        if not hasattr(self, "server_last_time_request"):
            setattr(self, "server_last_time_request", 0)

        if self.server_last_time_request == 0:
            self.server_last_time_request = int(t.time())
            self.per_connect_count = 0
        else:
            self.time_between_request = int(t.time() - self.server_last_time_request)

            if self.time_between_request == 0:
                self.per_connect_count += 1
            else:
                self.per_connect_count = 0
                self.server_last_time_request = int(t.time())

    def _can_process_client_request(self):

        if self.per_connect_count < self.server_max_clients:
            return True
        return False

    def _http_answers(self, code):

        try:
            http_json_message = json.dumps(self.http_messages[code]["json_message"])
            http_answer_template = f"{self.http_messages[code]['http_answer']}\nContent-Type: application/json\nContent-Length: {len(http_json_message)}\n\n{http_json_message}\n"
        except KeyError:
            logger.info(f"rule [{code}] Not Found")
            http_json_message = json.dumps(
                {"error": {"type": 500, "message": "Internal Server error"}}
            )
            http_answer_template = f"HTTP/1.1 500 Internal Server Error\nContent-Type: application/json\nContent-Length: {len(http_json_message)}\n\n{http_json_message}\n"

        return http_answer_template
