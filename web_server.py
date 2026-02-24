from enum import StrEnum
from http import HTTPStatus
from typing import Union, Mapping
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


def div(a: float, b: float) -> dict[str, float]:
    return {"result": a / b}


def add(a: float, b: float) -> dict[str, float]:
    return {"result": a + b}


@dataclass(frozen=True, slots=True)
class RequestTarget:
    path: str
    param: str


class ContentType(StrEnum):
    HTML = "text/html"
    PLAIN = "text/plain"
    JSON = "application/json"
    XML = "application/xml"


@dataclass(frozen=True, slots=True)
class RequestLine:
    method: str
    content_type: ContentType
    request_target: RequestTarget
    version: str


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
    http_version: str, status: int, content_type: str, response: Mapping[str, object]
) -> str:
    return f"{http_version} {status} {HTTPStatus(status).phrase}\r\nContent-Type: {content_type}\r\n\r\n{response}"


def path_handler(request_line: RequestLine) -> bytes:
    query_params = get_query(request_line.request_target.param)
    path = request_line.request_target.path
    html_message = ""
    match path:
        case "/":
            a = query_params.get("a")
            b = query_params.get("b")
            if a and b and a.isdigit() and b.isdigit():
                result = add(a=float(query_params["a"]), b=float(query_params["b"]))
                html_message = get_response(
                    http_version=request_line.version,
                    status=HTTPStatus.OK,
                    content_type=request_line.content_type,
                    response=result,
                )
            else:
                response_body = """
                        <html>
                        <head>
                        <meta charset="UTF-8">
                        </head>
                        <body>
                            <h2>Сложение</h2>
                            <form method="POST" action="/">
                                <input type="text" size=1 name="a"> + <input type="text" size=1 name="b">
                                <input type="submit" value="Решить">
                            </form>
                        </body>
                        </html>
                        """
                html_message = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(response_body.encode('utf-8'))}\r\n"
                    "\r\n" + response_body
                )
        case str() if path.startswith("/items/"):
            path_parts = path.strip("/").split("/")
            if len(path_parts) != 2 or not path_parts[1].isdigit():
                html_message = get_response(
                    http_version=request_line.version,
                    status=HTTPStatus.BAD_REQUEST,
                    content_type=request_line.content_type,
                    response={"detail": HTTPStatus.BAD_REQUEST.phrase},
                )
            else:
                path_params = {"item_id": int(path_parts[1])}
                body = read_item(
                    item_id=path_params["item_id"], q=query_params.get("q")
                )
                html_message = get_response(
                    http_version=request_line.version,
                    status=HTTPStatus.OK,
                    content_type=request_line.content_type,
                    response=body,
                )
        case "/div":
            query_params = dict(list(query_params.items())[:2])
            a = query_params.get("a")
            b = query_params.get("b")
            if a and b and a.isdigit() and b.isdigit() and int(b) > 0:
                result = div(a=float(query_params["a"]), b=float(query_params["b"]))
                html_message = get_response(
                    http_version=request_line.version,
                    status=HTTPStatus.OK,
                    content_type=request_line.content_type,
                    response=result,
                )
            else:
                html_message = get_response(
                    http_version=request_line.version,
                    status=HTTPStatus.BAD_REQUEST,
                    content_type=request_line.content_type,
                    response={"detail": HTTPStatus.BAD_REQUEST.phrase},
                )
        case _:
            html_message = get_response(
                http_version=request_line.version,
                status=HTTPStatus.NOT_FOUND,
                content_type=request_line.content_type,
                response={"detail": HTTPStatus.NOT_FOUND.phrase},
            )
    return bytes(html_message, encoding="UTF-8")


def response_type(data: list[str]) -> ContentType:
    headers = {}
    for i in data:
        header_split = i.split(": ", 1)
        if len(header_split) >= 2:
            key, value = header_split
            headers[key] = value

    for content in ContentType:
        accept = headers.get("Accept")
        if accept and content in accept:
            return ContentType(content)
    return ContentType.HTML


def parse_request_line(data: bytes) -> RequestLine:
    headers = data.decode("UTF-8").strip().split("\r\n")
    method, target, version = headers[0].split()
    content_type = response_type(headers[1:])
    if "?" in target:
        request_target = RequestTarget(*target.split("?"))
    elif method == "POST":
        request_target = RequestTarget(path=target, param=headers[-1])
    else:
        request_target = RequestTarget(path=target, param="")
    request_line = RequestLine(
        method=method,
        content_type=content_type,
        request_target=request_target,
        version=version,
    )
    return request_line


def main() -> None:
    address_type = socket.AF_INET
    protocol_type = socket.SOCK_STREAM
    server_address = ServerAddress(ip="127.0.0.1", port=8000)
    server = read_root(address_type, protocol_type, server_address)
    while True:
        client_socket, client_address = server.accept()
        print("Connected by", client_address)
        data = client_socket.recv(1024)
        request_line = parse_request_line(data=data)
        server_response = path_handler(request_line=request_line)
        client_socket.send(server_response)
        client_socket.close()


if __name__ == "__main__":
    main()
