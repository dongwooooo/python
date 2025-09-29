from fastapi import FastAPI
from typing import Annotated

app = FastAPI(title="Query Parameters")

@app.get("/items/")
def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

@app.get("/search")
def search_items(q: Annotated[str | None, "query string"] = None, short: bool = False):
    data = {"q": q}
    data["description"] = "short" if short else "long"
    return data
