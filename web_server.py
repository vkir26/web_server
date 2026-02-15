from http import HTTPStatus
from typing import Union
from dataclasses import dataclass
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


def read_item(item_id: int, q: Union[str, None] = None) -> dict[str, int | str | None]:
    return {"item_id": item_id, "q": q}


@dataclass(frozen=True, slots=True)
class RequestTarget:
    path: str
    param: str


@dataclass(frozen=True, slots=True)
class RequestLine:
    method: str
    request_target: RequestTarget
    version: str


def get_status(target_path: str) -> tuple[HTTPStatus, dict[str, int]]:
    path_params: dict[str, int] = {}
    if target_path == "/":
        return HTTPStatus.OK, path_params
    if target_path.startswith("/items/"):
        path_parts = target_path.strip("/").split("/")
        if len(path_parts) != 2 or not path_parts[1].isdigit():
            return HTTPStatus.BAD_REQUEST, path_params
        path_params["item_id"] = int(path_parts[1])
        return HTTPStatus.OK, path_params
    return HTTPStatus.NOT_FOUND, path_params


def get_query(target_param: str) -> dict[str, str]:
    query_params = {}
    for q in target_param.split("&"):
        if "=" in q:
            key, value = q.split("=", 1)
        else:
            key, value = q, ""
        query_params[key] = value
    return query_params


def get_response(
    http_ver: str, status: int, response: dict[str, int | str | None]
) -> str:
    return f"{http_ver} {status} {HTTPStatus(status).phrase}\r\nContent-Type: text/html\r\n\r\n{response}"


def path_handler(request_line: RequestLine) -> bytes:
    target = request_line.request_target
    status, path_params = get_status(target_path=target.path)
    html_message = ""
    match status:
        case HTTPStatus.OK:
            if target.path == "/":
                html_message = get_response(
                    request_line.version, status, {"Hello": "World"}
                )
            elif path_params.get("item_id") is not None:
                query_params = get_query(target.param)
                body = read_item(
                    item_id=path_params["item_id"], q=query_params.get("q")
                )
                html_message = get_response(request_line.version, status, body)
        case HTTPStatus.BAD_REQUEST | HTTPStatus.NOT_FOUND:
            html_message = get_response(
                request_line.version, status, {"detail": HTTPStatus(status).phrase}
            )
    return bytes(html_message, encoding="UTF-8")


def main() -> None:
    address_type = socket.AF_INET
    protocol_type = socket.SOCK_STREAM
    server_address = ServerAddress(ip="127.0.0.1", port=8000)
    server = read_root(address_type, protocol_type, server_address)
    while True:
        client_socket, client_address = server.accept()
        print("Connected by", client_address)
        data = client_socket.recv(1024)
        method, target, version = data.decode("UTF-8").strip().split("\r\n")[0].split()
        if "?" in target:
            request_target = RequestTarget(*target.split("?"))
        else:
            request_target = RequestTarget(path=target, param="")
        server_response = path_handler(
            request_line=RequestLine(
                method=method, request_target=request_target, version=version
            )
        )
        client_socket.send(server_response)
        client_socket.close()


if __name__ == "__main__":
    main()
