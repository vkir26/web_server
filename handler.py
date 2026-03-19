import re
from typing import Union, get_origin, get_args, Mapping, Callable, Any
import inspect
from dataclasses import dataclass
from http import HTTPStatus
from enum import StrEnum


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ServerResponse:
    response: str | dict[str, str | float]
    status_code: HTTPStatus


class Handler:
    def __init__(self) -> None:
        self.route: dict[str, Callable[..., Any]] = {}

    def trim_dict(
        self, params: dict[str, str], params_func: Mapping[str, inspect.Parameter]
    ) -> dict[str, str]:
        key = list(params.keys())[: len(params_func)]
        return {k: params[k] for k in key}

    def value_typing(
        self, all_params: dict[str, str], arg: inspect.Parameter
    ) -> dict[str, str]:
        value = all_params[arg.name]
        annotation = arg.annotation
        if get_origin(annotation) is Union:
            for arg_type in get_args(annotation):
                if arg_type is type(None):
                    continue
                all_params[arg.name] = arg_type(value)
        else:
            all_params[arg.name] = annotation(value)
        return all_params

    def get_query(self, target_param: str) -> dict[str, str]:
        query_params = {}
        for q in target_param.split("&"):
            if not q:
                continue
            if "=" in q:
                key, value = q.split("=", 1)
            else:
                key, value = q, ""
            query_params[key] = value
        return query_params

    def handle(self, user_path: str, q: str) -> ServerResponse:
        query_params = self.get_query(q)
        for path, func in self.route.items():
            for param in re.findall(r"{(\w+)}", path):
                path = path.replace(f"{{{param}}}", f"(?P<{param}>[^/]+)")

            match = re.fullmatch(path, user_path)
            if match:
                path_params = match.groupdict()
                all_params = path_params | query_params
                signature_func = inspect.signature(func)

                if len(all_params) != len(signature_func.parameters):
                    all_params = self.trim_dict(all_params, signature_func.parameters)

                try:
                    for arg in signature_func.parameters.values():
                        if (
                            arg.default is inspect.Parameter.empty
                            and arg.name not in all_params
                        ):
                            raise HTTPException(
                                status_code=HTTPStatus.BAD_REQUEST,
                                detail=HTTPStatus.BAD_REQUEST.phrase,
                            )

                        if arg.name in all_params:
                            try:
                                all_params = self.value_typing(
                                    all_params=all_params, arg=arg
                                )
                            except (ValueError, TypeError):
                                raise HTTPException(
                                    status_code=HTTPStatus.BAD_REQUEST,
                                    detail=HTTPStatus.BAD_REQUEST.phrase,
                                )
                        elif arg.name not in all_params and q != "":
                            q = str(list(query_params.keys())[0])
                            all_params.pop(q, None)

                    return ServerResponse(
                        response=func(**all_params), status_code=HTTPStatus.OK
                    )

                except HTTPException as e:
                    return ServerResponse(
                        response={"detail": e.detail},
                        status_code=HTTPStatus(e.status_code),
                    )

        return ServerResponse(
            response={"detail": HTTPStatus.NOT_FOUND.phrase},
            status_code=HTTPStatus.NOT_FOUND,
        )

    def get(self, path: str) -> Callable[..., Any]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.route[path] = func
            return func

        return decorator


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
