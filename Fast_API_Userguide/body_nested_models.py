from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="Body - Nested Models")

class Image(BaseModel):
    url: HttpUrl
    name: str

class Item(BaseModel):
    name: str
    images: list[Image] | None = None

@app.post("/items/")
def create_item(item: Item):
    return item
