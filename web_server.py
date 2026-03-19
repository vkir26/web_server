from dataclasses import dataclass
from handler import Handler, parse_request_line, RequestLine, ServerResponse
import socket


@dataclass(frozen=True, slots=True)
class ServerAddress:
    ip: str
    port: int


def read_root(
    address_type: socket.AddressFamily | int,
    protocol_type: socket.SocketKind | int,
    server_address: ServerAddress,
) -> socket.socket:
    server = socket.socket(address_type, protocol_type)
    server.bind((server_address.ip, server_address.port))
    server.listen(10)
    return server


def get_response(request_line: RequestLine, server_response: ServerResponse) -> bytes:
    return bytes(
        f"{request_line.version} {server_response.status_code} {server_response.status_code.phrase}\r\nContent-Type: {request_line.content_type}; charset=utf-8\r\n\r\n{server_response.response}",
        encoding="UTF-8",
    )


def root(app: Handler) -> None:
    address_type = socket.AF_INET
    protocol_type = socket.SOCK_STREAM
    server_address = ServerAddress(ip="127.0.0.1", port=8000)
    server = read_root(address_type, protocol_type, server_address)
    while True:
        client_socket, client_address = server.accept()
        print("Connected by", client_address)
        data = client_socket.recv(1024)
        request_line = parse_request_line(data=data)
        response = app.handle(
            request_line.request_target.path, request_line.request_target.param
        )
        server_response = get_response(
            request_line=request_line, server_response=response
        )
        client_socket.send(server_response)
        client_socket.close()
