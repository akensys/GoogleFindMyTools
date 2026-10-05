import threading
import time
import re

from NovaApi.ExecuteAction.LocateTracker.location_request import get_location_data_for_device
from NovaApi.ExecuteAction.PlaySound.start_sound_request import start_sound
from NovaApi.ExecuteAction.PlaySound.stop_sound_request import stop_sound
from NovaApi.ListDevices.nbe_list_devices import request_device_list
from ProtoDecoders.decoder import get_canonic_ids, parse_device_list_protobuf


class DeviceNotFoundError(Exception):
    pass


class TrackerService:
    def __init__(self, config, location_publisher):
        self.config = config
        self.location_publisher = location_publisher
        self._devices = {}
        self._devices_by_find_hub_uid = {}
        self._devices_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._monitor_thread = None

    def start(self):
        self.location_publisher.start()
        self.refresh_devices()
        if self.location_publisher.enabled:
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="googlefindmy-monitor",
                daemon=True,
            )
            self._monitor_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        self.location_publisher.stop()

    def refresh_devices(self):
        result_hex = request_device_list()
        if not result_hex:
            raise RuntimeError("Unable to retrieve the device list from Google.")

        devices = get_canonic_ids(parse_device_list_protobuf(result_hex))
        with self._devices_lock:
            self._devices = {device_id: name for name, device_id in devices}
            self._devices_by_find_hub_uid = {
                find_hub_uid.upper(): (device_id, name)
                for name, device_id in devices
                if (find_hub_uid := self._extract_find_hub_uid(name)) is not None
            }
        return self.list_devices()

    def list_devices(self):
        with self._devices_lock:
            return [
                {
                    "device_id": device_id,
                    "name": name,
                    "find_hub_uid": self._extract_find_hub_uid(name),
                }
                for device_id, name in self._devices.items()
            ]

    def locate(self, find_hub_uid, timeout_seconds=None, publish=True):
        device_id, name = self._get_device_by_find_hub_uid(find_hub_uid)
        return self._locate_device(
            device_id,
            name,
            timeout_seconds=timeout_seconds,
            publish=publish,
        )

    def _locate_device(self, device_id, name, timeout_seconds=None, publish=True):
        find_hub_uid = self._extract_find_hub_uid(name)
        locations = get_location_data_for_device(
            device_id,
            name,
            timeout_seconds=timeout_seconds or 60,
        )
        if locations is False:
            raise RuntimeError(f"Unable to locate {name}.")
        location = max(
            locations,
            key=lambda item: item.get("_timestamp", 0),
            default=None,
        )
        if location is not None:
            location = dict(location)
            location.pop("_timestamp", None)
        if publish:
            self.location_publisher.publish_location(
                device_id,
                name,
                find_hub_uid,
                location,
            )
        return {
            "device_id": device_id,
            "object_name": name,
            "find_hub_uid": find_hub_uid,
            "location": location,
        }

    def start_sound(self, find_hub_uid):
        device_id, name = self._get_device_by_find_hub_uid(find_hub_uid)
        if start_sound(device_id) is None:
            raise RuntimeError(f"Unable to send the start sound command to {name}.")
        return {
            "device_id": device_id,
            "object_name": name,
            "find_hub_uid": self._extract_find_hub_uid(name),
            "command": "start_sound",
            "accepted": True,
        }

    def stop_sound(self, find_hub_uid):
        device_id, name = self._get_device_by_find_hub_uid(find_hub_uid)
        if stop_sound(device_id) is None:
            raise RuntimeError(f"Unable to send the stop sound command to {name}.")
        return {
            "device_id": device_id,
            "object_name": name,
            "find_hub_uid": self._extract_find_hub_uid(name),
            "command": "stop_sound",
            "accepted": True,
        }

    @staticmethod
    def _extract_find_hub_uid(name):
        match = re.search(
            r"\bSN\s*[:#=_-]?\s*([A-Z0-9]+)\b",
            name,
            re.IGNORECASE,
        )
        return match.group(1) if match else None

    def _get_device_by_find_hub_uid(self, find_hub_uid):
        normalized_find_hub_uid = find_hub_uid.strip().upper()
        with self._devices_lock:
            device = self._devices_by_find_hub_uid.get(normalized_find_hub_uid)
        if device is None:
            self.refresh_devices()
            with self._devices_lock:
                device = self._devices_by_find_hub_uid.get(normalized_find_hub_uid)
        if device is None:
            raise DeviceNotFoundError(find_hub_uid)
        return device

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                # Refresh on every cycle so newly added or removed tags are reflected.
                devices = self.refresh_devices()
                for index, device in enumerate(devices):
                    if self._stop_event.is_set():
                        return
                    try:
                        self._locate_device(device["device_id"], device["name"])
                    except Exception as error:
                        print(f"[Monitor] Failed to locate {device['name']}: {error}")
                    if index < len(devices) - 1:
                        self._stop_event.wait(self.config.device_interval_seconds)
            except Exception as error:
                print(f"[Monitor] Cycle failed: {error}")

            self._stop_event.wait(self.config.monitor_interval_seconds)
