import requests
from prefect import task


@task
def fetch_current_time() -> str:
    resp = requests.get(
        "http://worldtimeapi.org/api/timezone/Etc/UTC", timeout=10
    )
    resp.raise_for_status()
    return resp.json()["datetime"]
