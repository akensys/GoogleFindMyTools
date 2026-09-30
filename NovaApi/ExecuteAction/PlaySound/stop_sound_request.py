#
#  GoogleFindMyTools - A set of tools to interact with the Google Find My API
#  Copyright © 2024 Leon Böttger. All rights reserved.
#
from Auth.fcm_receiver import FcmReceiver
from NovaApi.ExecuteAction.PlaySound.sound_request import create_sound_request
from NovaApi.nova_request import nova_request
from NovaApi.scopes import NOVA_ACTION_API_SCOPE
from example_data_provider import get_example_data


def stop_sound(canonic_device_id):
    """Stop a device's sound and return the Nova API response."""
    fcm_token = FcmReceiver().get_registration_token()
    hex_payload = create_sound_request(False, canonic_device_id, fcm_token)
    return nova_request(NOVA_ACTION_API_SCOPE, hex_payload)


if __name__ == '__main__':
    sample_canonic_device_id = get_example_data("sample_canonic_device_id")
    stop_sound(sample_canonic_device_id)
