#
#  GoogleFindMyTools - A set of tools to interact with the Google Find My API
#  Copyright © 2024 Leon Böttger. All rights reserved.
#

import binascii
import requests
from bs4 import BeautifulSoup

from Auth.aas_token_retrieval import get_aas_token
from Auth.adm_token_retrieval import get_adm_token
from Auth.username_provider import get_username


class NovaRateLimitError(Exception):
    def __init__(self, retry_after=None):
        super().__init__("Google rate limit reached. Try again later.")
        self.retry_after = retry_after


def nova_request(api_scope, hex_payload):
    url = "https://android.googleapis.com/nova/" + api_scope

    android_device_manager_oauth_token = get_adm_token(get_username())

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Authorization": "Bearer " + android_device_manager_oauth_token,
        "Accept-Language": "en-US",
        "User-Agent": "fmd/20006320; gzip"
    }

    payload = binascii.unhexlify(hex_payload)

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=30)
    except requests.RequestException as error:
        print(f"[NovaRequest] Request failed: {error}")
        return None

    if response.status_code == 200:
        return response.content.hex()

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        print(f"[NovaRequest] Too many requests. Retry-After: {retry_after}")
        raise NovaRateLimitError(retry_after=retry_after)

    soup = BeautifulSoup(response.text, 'html.parser')
    print("[NovaRequest] Error: ", soup.get_text())


if __name__ == '__main__':
    print(get_aas_token())