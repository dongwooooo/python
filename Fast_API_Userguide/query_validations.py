from fastapi import FastAPI, Query
from typing import List

app = FastAPI(title="Query Validations")

@app.get("/validate")
def validate_q(
    q: str | None = Query(
        default=None,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9 _-]+$",
        description="3~50자, 영문/숫자/공백/언더스코어/대시 허용",
    ),
    tags: List[str] = Query(default=[], description="여러 개 전달하려면 ?tags=a&tags=b"),
):
    return {"q": q, "tags": tags}
