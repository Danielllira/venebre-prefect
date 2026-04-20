from prefect import task

from pipelines.utils.dates import now
from pipelines.utils.logger import log


@task
def extract_weather_data() -> dict:
    extracted_at = now()
    log(f"teste acontecendo em {extracted_at}")
    return {
        "source": "api_weather_data",
        "status": "ok",
        "extracted_at": extracted_at,
    }
