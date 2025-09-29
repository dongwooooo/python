from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field

app = FastAPI(title="Query Parameter Models")

class Filters(BaseModel):
    q: str | None = Field(default=None, description="검색어")
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=10, ge=1, le=100)

def get_filters(
    q: str | None = None,
    skip: int = 0,
    limit: int = 10,
) -> Filters:
    return Filters(q=q, skip=skip, limit=limit)

@app.get("/items")
def list_items(filters: Filters = Depends(get_filters)):
    # 실제로는 filters를 사용해 DB 조회 등을 수행
    return {"filters": filters}
