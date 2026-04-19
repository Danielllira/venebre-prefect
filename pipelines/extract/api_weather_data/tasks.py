from prefect import task

@task
def extract_weather_data() -> dict:
    return {"source": "api_weather_data", "status": "ok"}