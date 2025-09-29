from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Request Body")

class Item(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = Field(None, max_length=300)
    price: float = Field(..., gt=0)
    tax: float | None = Field(None, ge=0)

@app.post("/items/")
def create_item(item: Item):
    total = item.price + (item.tax or 0)
    return {"item": item, "total": total}
