from fastapi import FastAPI, Body
from pydantic import BaseModel, Field

app = FastAPI(title="Body - Multiple Parameters")

class Item(BaseModel):
    name: str
    price: float

class User(BaseModel):
    username: str
    full_name: str | None = None

@app.post("/purchase/")
def purchase(
    item: Item,
    user: User,
    importance: int = Body(..., gt=0, description="중요도(>0)"),
):
    return {"item": item, "user": user, "importance": importance}
