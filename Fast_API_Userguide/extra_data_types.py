from datetime import datetime, time, timedelta
from uuid import UUID
from fastapi import FastAPI, Body

app = FastAPI(title="Extra Data Types")

@app.post("/items/{item_id}")
def read_item(
    item_id: UUID,
    start_datetime: datetime = Body(...),
    end_datetime: datetime = Body(...),
    process_after: time = Body(..., description="하루 중 특정 시간"),
    repeat_every: timedelta = Body(..., description="반복 주기"),
):
    duration = end_datetime - start_datetime
    return {
        "item_id": str(item_id),
        "duration": duration,
        "process_after": process_after,
        "repeat_every_seconds": repeat_every.total_seconds(),
    }
