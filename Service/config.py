import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv()


def _get_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value
    return default


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_mqtt_endpoint() -> tuple[str, int, bool]:
    url = os.getenv("MQTT_GTW_CONNECT_PLUS_URL", "").strip()
    if not url:
        return (
            os.getenv("MQTT_HOST", ""),
            int(os.getenv("MQTT_PORT", "1883")),
            _get_bool("MQTT_TLS"),
        )

    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError(
            "MQTT_GTW_CONNECT_PLUS_URL must be a URL such as "
            "ssl://broker.example.com:8883"
        )

    tls = parsed.scheme.lower() in {"mqtts", "ssl", "tls"}
    default_port = 8883 if tls else 1883
    return parsed.hostname, parsed.port or default_port, tls


_MQTT_HOST, _MQTT_PORT, _MQTT_TLS = _get_mqtt_endpoint()


@dataclass(frozen=True)
class ServiceConfig:
    mqtt_host: str = _MQTT_HOST
    mqtt_port: int = _MQTT_PORT
    mqtt_topic: str = _get_env(
        "MQTT_CONNECT_PLUS_TOPICS_0",
        "MQTT_TOPIC",
        default="googlefindmy/location",
    )
    mqtt_username: str = _get_env(
        "MQTT_GTW_CONNECT_PLUS_USERNAME", "MQTT_USERNAME"
    )
    mqtt_password: str = _get_env(
        "MQTT_GTW_CONNECT_PLUS_PASSWORD", "MQTT_PASSWORD"
    )
    mqtt_client_id: str = _get_env(
        "MQTT_GTW_CONNECT_PLUS_CLIENT_ID",
        "MQTT_CLIENT_ID",
        default="googlefindmytools",
    )
    mqtt_qos: int = 1
    mqtt_retain: bool = False
    mqtt_tls: bool = _MQTT_TLS
    device_interval_seconds: int = 2
    monitor_interval_seconds: int = 2

CONFIG = ServiceConfig()
