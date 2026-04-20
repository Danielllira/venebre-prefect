from prefect import task
from datetime import datetime


@task
def extract_weather_data() -> dict:
    now = datetime.now()
    return {"source": "api_weather_data", "status": "ok", "extracted_at": now}
