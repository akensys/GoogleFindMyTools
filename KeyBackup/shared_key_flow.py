#
#  GoogleFindMyTools - A set of tools to interact with the Google Find My API
#  Copyright © 2024 Leon Böttger. All rights reserved.
#

import json

from selenium.common.exceptions import NoAlertPresentException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from Auth.google_login import (
    automate_google_sign_in,
    save_auth_diagnostic,
    select_security_device_if_requested,
    submit_lockscreen_pin_if_requested,
)
from KeyBackup.response_parser import get_fmdn_shared_key
from KeyBackup.shared_key_request import get_security_domain_request_url
from chrome_driver import create_driver

def request_shared_key_flow():
    driver = create_driver()
    try:
        # Open Google accounts sign-in page
        driver.get("https://accounts.google.com/")

        automate_google_sign_in(
            driver,
            completed=lambda current_driver: "myaccount.google.com" in current_driver.current_url,
        )
        print("[SharedKeyFlow] Signed in successfully.")

        # Open the security domain request URL
        # Inject JavaScript interface
        script = """
        window.mm = {
            setVaultSharedKeys: function(str, vaultKeys) {
                console.log('setVaultSharedKeys called with:', str, vaultKeys);
                alert(JSON.stringify({ method: 'setVaultSharedKeys', str: str, vaultKeys: vaultKeys }));
            },
            closeView: function() {
                console.log('closeView called');
                alert(JSON.stringify({ method: 'closeView' }));
            }
        };
        """
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": script},
        )

        security_url = get_security_domain_request_url()
        driver.get(security_url)
        select_security_device_if_requested(driver)
        submit_lockscreen_pin_if_requested(driver)

        try:
            alert = driver.switch_to.alert
        except NoAlertPresentException:
            # Also install the interface in the current document as a fallback.
            driver.execute_script(script)
            try:
                alert = WebDriverWait(driver, 300).until(ec.alert_is_present())
            except TimeoutException as error:
                screenshot = save_auth_diagnostic(driver)
                raise TimeoutError(
                    "Google did not return the shared key within 5 minutes. "
                    f"Current URL: {driver.current_url}. Screenshot: {screenshot}"
                ) from error

        data = json.loads(alert.text)
        alert.accept()
        if data.get("method") != "setVaultSharedKeys":
            raise RuntimeError(
                f"Google closed the shared-key flow without returning a key: {data}"
            )

        shared_key = get_fmdn_shared_key(data["vaultKeys"])
        print("[SharedKeyFlow] Received Shared Key.")
        return shared_key.hex()

    except Exception as e:
        print(f"An error occurred: {e}")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
   request_shared_key_flow()
