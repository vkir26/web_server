from enum import IntEnum
from typing import Union
from dataclasses import dataclass
import socket


def read_root() -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 8000))
    server.listen(10)
    return server


def read_item(item_id: int, q: Union[str, None] = None) -> dict[str, int | str | None]:
    return {"item_id": item_id, "q": q}


@dataclass(frozen=True, slots=True)
class RequestLine:
    method: str
    path: str
    version: str


class HttpStatusCode(IntEnum):
    Success = 200
    BadRequest = 400
    NotFound = 404


def get_status(request_line: RequestLine) -> tuple[HttpStatusCode, dict[str, int]]:
    path_only = request_line.path.split("?", 1)[0]
    path_params = {}
    if path_only == "/":
        status = HttpStatusCode.Success
    elif path_only.startswith("/items/"):
        try:
            pathname, item_id = path_only.split("/")[1:3]
            path_params["item_id"] = int(item_id)
        except ValueError:
            status = HttpStatusCode.BadRequest
        else:
            status = HttpStatusCode.Success
    else:
        status = HttpStatusCode.NotFound
    return status, path_params


def get_query(path: str) -> dict[str, str]:
    query_params = {}
    if "?" in path:
        for i in path.split("?")[1].split("&"):
            if "=" in i:
                key, value = i.split("=", 1)
                query_params[key] = value
            elif i:
                key, value = i, ""
                query_params[key] = value
    return query_params


def get_response(status: int) -> str:
    status_text = {
        HttpStatusCode.Success: "OK",
        HttpStatusCode.BadRequest: "Bad Request",
        HttpStatusCode.NotFound: "Not Found",
    }
    return (
        f"HTTP/1.1 {status} {status_text[HttpStatusCode(status)]}\r\n"
        + "Content-Type: text/html\r\n\r\n{}"
    )


def path_handler(request_line: RequestLine) -> bytes:
    path_only = request_line.path.split("?", 1)[0]
    status, path_params = get_status(request_line=request_line)
    query_params = get_query(request_line.path)
    http_response = get_response(status)
    html_message = ""
    match status:
        case HttpStatusCode.Success:
            if path_only == "/":
                html_message = http_response.format({"Hello": "World"})
            elif path_params.get("item_id") is not None:
                body = read_item(
                    item_id=path_params["item_id"], q=query_params.get("q")
                )
                html_message = http_response.format(body)
        case HttpStatusCode.BadRequest:
            html_message = http_response.format({"detail": "Bad Request"})
        case HttpStatusCode.NotFound:
            html_message = http_response.format({"detail": "Not Found"})
    return bytes(html_message, encoding="UTF-8")


def main() -> None:
    server = read_root()
    while True:
        client_socket, client_address = server.accept()
        print("Connected by", client_address)
        data = client_socket.recv(1024)
        request_line = RequestLine(
            *data.decode("UTF-8").strip().split("\r\n")[0].split()
        )
        client_socket.send(path_handler(request_line))
        client_socket.close()


if __name__ == "__main__":
    main()
