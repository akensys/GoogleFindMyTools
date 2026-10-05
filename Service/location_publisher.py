import json
import threading

import paho.mqtt.client as mqtt


class LocationPublisher:
    def __init__(self, config):
        self.config = config
        self._connected = threading.Event()
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=config.mqtt_client_id,
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        if config.mqtt_username:
            self._client.username_pw_set(
                config.mqtt_username,
                config.mqtt_password or None,
            )
        if config.mqtt_tls:
            self._client.tls_set()

    @property
    def enabled(self):
        return bool(self.config.mqtt_host)

    def start(self):
        if not self.enabled:
            print(
                "[LocationPublisher] No MQTT_HOST configured; "
                "periodic updates are not started."
            )
            return

        self._client.connect_async(self.config.mqtt_host, self.config.mqtt_port)
        self._client.loop_start()
        print(
            f"[LocationPublisher] Connecting to MQTT broker "
            f"{self.config.mqtt_host}:{self.config.mqtt_port}..."
        )

    def stop(self):
        if not self.enabled:
            return
        self._client.disconnect()
        self._client.loop_stop()
        self._connected.clear()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self._connected.set()
            print("[LocationPublisher] Connected to MQTT broker.")
        else:
            self._connected.clear()
            print(f"[LocationPublisher] MQTT connection failed: {reason_code}")

    def _on_disconnect(
        self,
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties,
    ):
        self._connected.clear()
        if reason_code != 0:
            print(f"[LocationPublisher] MQTT connection lost: {reason_code}")

    def publish_location(self, device_id, name, find_hub_uid, location):
        if not self.enabled or not location:
            return False

        payload = {
            "device_id": device_id,
            "object_name": name,
            "find_hub_uid": find_hub_uid,
            "location": location,
        }

        if not self._connected.wait(timeout=10):
            print(
                f"[LocationPublisher] Update failed for {name} "
                f"({device_id}): MQTT broker is not connected"
            )
            return False

        message = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        info = self._client.publish(
            self.config.mqtt_topic,
            message,
            qos=self.config.mqtt_qos,
            retain=self.config.mqtt_retain,
        )
        try:
            info.wait_for_publish(timeout=10)
        except RuntimeError as error:
            print(
                f"[LocationPublisher] Update failed for {name} "
                f"({device_id}): {error}"
            )
            return False

        if info.rc != mqtt.MQTT_ERR_SUCCESS or not info.is_published():
            print(
                f"[LocationPublisher] Update failed for {name} "
                f"({device_id}): MQTT error {info.rc}"
            )
            return False

        print(
            f"[LocationPublisher] Location sent for {name} ({device_id}): "
            f"topic={self.config.mqtt_topic} time={location.get('time')} "
        )
        return True
