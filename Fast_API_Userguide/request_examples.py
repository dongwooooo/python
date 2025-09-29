from fastapi import FastAPI, Body
from pydantic import BaseModel

app = FastAPI(title="Declare Request Example Data")

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.post("/items/")
def create_item(
    item: Item = Body(
        ...,
        examples={
            "basic": {
                "summary": "기본 예시",
                "value": {"name": "Laptop", "price": 1200.0}
            },
            "with_description": {
                "summary": "설명 포함",
                "value": {"name": "Monitor", "description": "27-inch", "price": 300.0}
            },
            "with_tax": {
                "summary": "세금 포함",
                "value": {"name": "Phone", "price": 800.0, "tax": 80.0}
            },
        },
    )
):
    return item
