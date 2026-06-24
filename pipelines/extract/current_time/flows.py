from prefect import flow
from pipelines.extract.current_time.tasks import fetch_current_time


@flow(name='Extract: Current Time', log_prints=True)
def current_time():
    result = fetch_current_time()
    print(f"Current UTC time: {result}")
    return result


pipelines = [
    {
        "flow": current_time,
        "tags": ["extract", "time"],
        "schedule": None,
    },
]
