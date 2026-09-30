import uvicorn

from Service.config import CONFIG


if __name__ == "__main__":
    uvicorn.run(
        "Service.api:app",
        host=CONFIG.api_host,
        port=CONFIG.api_port,
        reload=False,
    )
