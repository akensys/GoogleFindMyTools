import os
import time

from dotenv import load_dotenv
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoAlertPresentException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


load_dotenv()


def _action_delay():
    return max(0.0, float(os.getenv("SELENIUM_ACTION_DELAY_SECONDS", "2")))


def _pause_before_action():
    time.sleep(_action_delay())


class GoogleCredentialsError(RuntimeError):
    pass


def get_google_credentials():
    email = os.getenv("GOOGLE_EMAIL", "").strip()
    password = os.getenv("GOOGLE_PASSWORD", "")
    if not email or not password:
        raise GoogleCredentialsError(
            "GOOGLE_EMAIL and GOOGLE_PASSWORD must be configured in .env."
        )
    return email, password


def automate_google_sign_in(driver, completed, timeout=300):
    """Fill Google credentials and consent screens while allowing manual MFA."""
    email, password = get_google_credentials()
    deadline = time.monotonic() + timeout
    announced_mfa_wait = False

    while time.monotonic() < deadline:
        if completed(driver):
            return

        acted = False
        acted |= _fill_visible(driver, (By.ID, "identifierId"), email)
        acted |= _fill_visible(driver, (By.NAME, "Passwd"), password)

        if acted:
            _pause_before_action()
            _click_action(driver, ("Suivant", "Next"))
            announced_mfa_wait = False
        elif _action_is_visible(
            driver,
            ("J'accepte", "J’accepte", "I agree", "Accepter"),
        ):
            _pause_before_action()
            if _click_action(
                driver,
                ("J'accepte", "J’accepte", "I agree", "Accepter"),
            ):
                announced_mfa_wait = False
        elif not announced_mfa_wait:
            print(
                "[GoogleLogin] Waiting for manual confirmation/MFA if Google "
                "requests it..."
            )
            announced_mfa_wait = True

        time.sleep(1)

    raise TimeoutError("Google authentication did not complete within 5 minutes.")


def wait_for_google_session(driver, timeout=60):
    """Wait until Google has finished establishing the authenticated session."""
    authentication_cookies = {
        "SID",
        "SAPISID",
        "__Secure-1PSID",
        "__Secure-3PSID",
    }

    WebDriverWait(driver, timeout).until(
        lambda current_driver: (
            current_driver.execute_script("return document.readyState") == "complete"
            and any(
                cookie.get("name") in authentication_cookies
                for cookie in current_driver.get_cookies()
            )
        )
    )
    # Let Google's redirects and cookie synchronization settle before opening
    # the encryption-unlock page.
    time.sleep(2)
    print("[GoogleLogin] Google session is ready.")


def submit_lockscreen_pin_if_requested(driver, timeout=60):
    pin = os.getenv("GOOGLE_LOCKSCREEN_PIN", "")
    if not pin:
        return False

    try:
        result = WebDriverWait(driver, timeout).until(
            lambda current_driver: _lockscreen_pin_or_alert(current_driver)
        )
    except TimeoutException:
        screenshot = save_auth_diagnostic(driver)
        raise TimeoutError(
            "Google lock-screen PIN field was not found. "
            f"Current URL: {driver.current_url}. Screenshot: {screenshot}"
        )

    if result == "alert":
        print("[GoogleLogin] Google returned the security response without a PIN prompt.")
        return False

    field = result
    field.clear()
    field.send_keys(pin)
    _pause_before_action()
    try:
        WebDriverWait(driver, 30).until(
            lambda current_driver: _click_action(
                current_driver, ("Suivant", "Next")
            )
        )
    except TimeoutException as error:
        raise RuntimeError(
            "Unable to submit the Google lock-screen PIN."
        ) from error
    print("[GoogleLogin] Lock-screen PIN submitted.")
    return True


def select_security_device_if_requested(driver, timeout=30):
    try:
        result = WebDriverWait(driver, timeout).until(
            lambda current_driver: (
                "pin"
                if _find_lockscreen_pin(current_driver)
                else _visible_element(
                    current_driver,
                    (By.CSS_SELECTOR, "p.HVc8K[jsname='MZArnb']"),
                )
            )
        )
    except TimeoutException:
        return False

    if result == "pin":
        return False
    entry = result

    clickable = entry
    try:
        clickable = entry.find_element(
            By.XPATH,
            "./ancestor::*[@role='button'][1] | ./ancestor::button[1]",
        )
    except NoSuchElementException:
        pass

    _pause_before_action()
    clickable.click()
    print("[GoogleLogin] Security device selected.")
    return True


def save_auth_diagnostic(driver):
    path = os.path.join(os.path.dirname(__file__), "google-login-error.png")
    driver.save_screenshot(path)
    return path


def _find_lockscreen_pin(driver):
    locators = (
        (By.NAME, "knowledgeLockscreenPinPasswordResponse"),
        (By.CSS_SELECTOR, "input[type='password'][inputmode='numeric']"),
        (
            By.XPATH,
            "//input[contains(@aria-label, 'code') or "
            "contains(@aria-label, 'Code')]",
        ),
    )
    for locator in locators:
        element = _visible_element(driver, locator)
        if element is not None:
            return element
    return None


def _lockscreen_pin_or_alert(driver):
    try:
        driver.switch_to.alert
        return "alert"
    except NoAlertPresentException:
        return _find_lockscreen_pin(driver)


def _fill_visible(driver, locator, value):
    element = _visible_element(driver, locator)
    if element is None:
        return False
    if not element.get_attribute("value"):
        _pause_before_action()
        element.clear()
        element.send_keys(value)
    return True


def _visible_element(driver, locator):
    try:
        element = driver.find_element(*locator)
        return element if element.is_displayed() and element.is_enabled() else None
    except (NoSuchElementException, StaleElementReferenceException):
        return None


def _click_action(driver, labels):
    elements = _action_elements(driver, labels)
    try:
        for element in elements:
            if element.is_displayed() and element.is_enabled():
                element.click()
                return True
    except (ElementClickInterceptedException, StaleElementReferenceException):
        return False
    return False


def _action_is_visible(driver, labels):
    try:
        return any(
            element.is_displayed() and element.is_enabled()
            for element in _action_elements(driver, labels)
        )
    except StaleElementReferenceException:
        return False


def _action_elements(driver, labels):
    label_test = " or ".join(
        f"normalize-space()={_xpath_literal(label)}" for label in labels
    )
    xpath = (
        f"//button[.//span[{label_test}]]"
        f" | //*[@role='button'][.//span[{label_test}]]"
    )
    return driver.find_elements(By.XPATH, xpath)


def _xpath_literal(value):
    if "'" not in value:
        return f"'{value}'"
    parts = value.split("'")
    return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"
