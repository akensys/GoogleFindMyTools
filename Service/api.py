from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool

from Service.config import CONFIG
from Service.location_publisher import LocationPublisher
from Service.tracker_service import DeviceNotFoundError, TrackerService
from NovaApi.nova_request import NovaRateLimitError


location_publisher = LocationPublisher(CONFIG)
tracker_service = TrackerService(CONFIG, location_publisher)

app = FastAPI(title="GoogleFindMyTools API", version="1.0.0")


def require_api_key(x_api_key: str | None = Header(default=None)):
    if CONFIG.api_key and x_api_key != CONFIG.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )


@app.on_event("startup")
def startup():
    tracker_service.start()


@app.on_event("shutdown")
def shutdown():
    tracker_service.stop()


@app.post("/locate/{device_id}", dependencies=[Depends(require_api_key)])
async def locate(device_id: str, timeout_seconds: int | None = Query(default=None, ge=1, le=180)):
    try:
        return await run_in_threadpool(tracker_service.locate, device_id, timeout_seconds)
    except DeviceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Unknown device.") from error
    except NovaRateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail="Too many requests sent to Google. Try again later.",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/start-sound/{device_id}/", dependencies=[Depends(require_api_key)])
async def sound_start(device_id: str):
    try:
        return await run_in_threadpool(tracker_service.start_sound, device_id)
    except DeviceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Unknown device.") from error
    except NovaRateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail="Too many requests sent to Google. Try again later.",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/stop-sound/{device_id}/", dependencies=[Depends(require_api_key)])
async def sound_stop(device_id: str):
    try:
        return await run_in_threadpool(tracker_service.stop_sound, device_id)
    except DeviceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Unknown device.") from error
    except NovaRateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail="Too many requests sent to Google. Try again later.",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
