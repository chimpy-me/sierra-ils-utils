import logging
import pytest
import requests
from sierra_ils_utils.decorators import hybrid_retry_decorator, authenticate
import time
from unittest.mock import Mock, call, patch

logger = logging.getLogger('__name__')

# Create a mock function that will always raise an exception
mock_function = Mock(
    side_effect=Exception("Forced exception for testing")
)

def test_hybrid_retry_decorator():
    class DummyClass:
        def __init__(self):
            self.logger = logger

        @hybrid_retry_decorator(max_retries=4, initial_wait_time=1)
        def failing_method(self):
            raise Exception("This method always fails")

    dummy = DummyClass()
    with pytest.raises(Exception, match="This method always fails"):
        dummy.failing_method()


def test_hybrid_retry_decorator_jitter():
    class DummyClass:
        def __init__(self):
            self.logger = logger
            self.sleep_times = []

        @hybrid_retry_decorator(max_retries=4, initial_wait_time=1)
        def failing_method(self):
            raise Exception("This method always fails")

    # Override sleep method to capture sleep times
    original_sleep = time.sleep
    def mock_sleep(seconds):
        dummy.sleep_times.append(seconds)
        original_sleep(0.1)  # We sleep for only a fraction to speed up the test

    time.sleep = mock_sleep

    dummy = DummyClass()
    with pytest.raises(Exception, match="This method always fails"):
        dummy.failing_method()

    # Restore original sleep
    time.sleep = original_sleep

    expected_times = [1, 1.5, 2.25, 3.38]  # Without jitter

    # Check if each actual sleep time is within 10% of the expected time
    for actual, expected in zip(dummy.sleep_times, expected_times):
        assert 0.9 * expected <= actual <= 1.1 * expected

# not testing the authenticate decorator here, since it's more integrated into the SierraAPIv6 module
