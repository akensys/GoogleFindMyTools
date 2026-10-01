from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from Service.config import CONFIG
from Service.location_publisher import LocationPublisher
from Service.tracker_service import DeviceNotFoundError, TrackerService
from NovaApi.nova_request import NovaRateLimitError


location_publisher = LocationPublisher(CONFIG)
tracker_service = TrackerService(CONFIG, location_publisher)

app = FastAPI(title="GoogleFindMyTools API", version="1.0.0")

@app.on_event("startup")
def startup():
    tracker_service.start()


@app.on_event("shutdown")
def shutdown():
    tracker_service.stop()


@app.post("/locate/{serial_number}")
async def locate(serial_number: str, timeout_seconds: int | None = Query(default=None, ge=1, le=180)):
    try:
        return await run_in_threadpool(tracker_service.locate, serial_number, timeout_seconds)
    except DeviceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Unknown serial number.") from error
    except NovaRateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail="Too many requests sent to Google. Try again later.",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/start-sound/{serial_number}")
async def sound_start(serial_number: str):
    try:
        return await run_in_threadpool(tracker_service.start_sound, serial_number)
    except DeviceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Unknown serial number.") from error
    except NovaRateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail="Too many requests sent to Google. Try again later.",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/stop-sound/{serial_number}")
async def sound_stop(serial_number: str):
    try:
        return await run_in_threadpool(tracker_service.stop_sound, serial_number)
    except DeviceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Unknown serial number.") from error
    except NovaRateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail="Too many requests sent to Google. Try again later.",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
