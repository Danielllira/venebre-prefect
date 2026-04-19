from prefect import flow

from pipelines.extract.api_weather_data.tasks import extract_weather_data


@flow(name="Extract - API Weather Data")
def api_weather_data(env: str = "dev") -> dict:
    data = extract_weather_data()
    print(f"Running in env={env}")
    return data