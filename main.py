from typing import Union
from app.web_server import root
from app.handler import Handler, HTTPException

app = Handler()


@app.get(path="/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None) -> dict[str, int | str | None]:
    return {"item_id": item_id, "q": q}


@app.get("/div")
def div(a: float, b: float) -> dict[str, float]:
    if b == 0:
        raise HTTPException(status_code=400, detail="Деление на ноль невозможно")
    return {"result": a / b}


def main() -> None:
    root(app=app)


if __name__ == "__main__":
    main()
