from fastapi import FastAPI, Path

app = FastAPI(title="Path Numeric Validations")

@app.get("/items/{item_id}")
def get_item(
    item_id: int = Path(..., gt=0, le=1000, description="1~1000 사이 정수"),
):
    return {"item_id": item_id}
