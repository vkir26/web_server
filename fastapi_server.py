from typing import Union

from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None) -> dict[str, int | str | None]:
    return {"item_id": item_id, "q": q}


@app.get("/div")
def div(a: float, b: float) -> dict[str, float]:
    if b == 0:
        raise HTTPException(status_code=400, detail="Деление на ноль невозможно")
    return {"result": a / b}
