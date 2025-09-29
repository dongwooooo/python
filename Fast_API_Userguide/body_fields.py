from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Body - Fields")

class Item(BaseModel):
    title: str = Field(..., min_length=3, max_length=50, description="상품명")
    price: float = Field(..., gt=0, description="가격(>0)")
    tags: list[str] = Field(default_factory=list, description="태그 목록")

@app.post("/items/")
def create_item(item: Item):
    return item
