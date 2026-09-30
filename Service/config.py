import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ServiceConfig:
    api_base_url: str = os.getenv("API_BASE_URL", "http://127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8080"))
    api_key: str = os.getenv("API_KEY", "")

    mqtt_host: str = os.getenv("MQTT_HOST", "")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic: str = os.getenv("MQTT_TOPIC", "googlefindmy/location")
    mqtt_username: str = os.getenv("MQTT_USERNAME", "")
    mqtt_password: str = os.getenv("MQTT_PASSWORD", "")
    mqtt_client_id: str = os.getenv("MQTT_CLIENT_ID", "googlefindmytools")
    mqtt_qos: int = 1
    mqtt_retain: bool = False
    mqtt_tls: bool = False
    device_interval_seconds: int = 2
    monitor_interval_seconds: int = 2

    @property
    def api_host(self):
        return urlparse(self.api_base_url).hostname or "127.0.0.1"


CONFIG = ServiceConfig()
