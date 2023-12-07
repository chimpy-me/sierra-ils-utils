import pytest
import httpx
from sierra_ils_utils.decorators import hybrid_retry_decorator
from sierra_ils_utils import SierraAPIResponse
from unittest.mock import Mock

def test_hybrid_retry_decorator():
    class DummyClass:
        def __init__(self):
            self.attempt_count = 0

        @hybrid_retry_decorator(max_retries=3, initial_wait_time=0.1, initial_exponential_factor=1, initial_retries=3, fixed_interval=0.1)
        def method_with_retries(self):
            if self.attempt_count < 2:  # Fail twice before succeeding
                self.attempt_count += 1
                raise httpx.ConnectError("Transient connection error")

            # Option 1: Return a mock SierraAPIResponse
            # return Mock(spec=SierraAPIResponse)

            # Option 2: Return a simple SierraAPIResponse instance (if feasible)
            return SierraAPIResponse(response_model_name="Dummy", data={}, raw_response=Mock(spec=httpx.Response))

    dummy = DummyClass()
    result = dummy.method_with_retries()

    # Verify the result is an instance of SierraAPIResponse (for option 1)
    assert isinstance(result, SierraAPIResponse)

    # The method should initially fail twice, then succeed on the third attempt
    assert dummy.attempt_count == 2


import pytest
import asyncio
import httpx
from sierra_ils_utils.decorators import hybrid_retry_decorator
from sierra_ils_utils import SierraAPIResponse
from unittest.mock import Mock

@pytest.mark.asyncio
async def test_hybrid_retry_decorator_async():
    class DummyAsyncClass:
        def __init__(self):
            self.attempt_count = 0

        @hybrid_retry_decorator(max_retries=3, initial_wait_time=0.1, initial_exponential_factor=1, initial_retries=3, fixed_interval=0.1)
        async def async_method_with_retries(self):
            if self.attempt_count < 2:  # Fail twice before succeeding
                self.attempt_count += 1
                raise httpx.ConnectError("Transient connection error")

            # Return a simple SierraAPIResponse instance
            return SierraAPIResponse(response_model_name="Dummy", data={}, raw_response=Mock(spec=httpx.Response))

    dummy = DummyAsyncClass()
    result = await dummy.async_method_with_retries()

    # Verify the result is an instance of SierraAPIResponse
    assert isinstance(result, SierraAPIResponse)

    # The method should initially fail twice, then succeed on the third attempt
    assert dummy.attempt_count == 2


import pytest
import httpx
from sierra_ils_utils.decorators import hybrid_retry_decorator
from sierra_ils_utils import SierraAPIResponse
from unittest.mock import Mock

def test_hybrid_retry_decorator_transient_failures():
    class DummyClass:
        def __init__(self):
            self.attempt_count = 0

        @hybrid_retry_decorator(
                max_retries=3,  # Will retry three times
                initial_wait_time=0.1, 
                initial_exponential_factor=1, 
                initial_retries=3, 
                fixed_interval=0.1
        )
        def transient_failure_method(self):
            # Fail three times before succeeding
            if self.attempt_count < 3:
                self.attempt_count += 1
                raise httpx.ConnectError("Transient connection error")

            # This line should never be reached
            return SierraAPIResponse(
                response_model_name="Dummy", 
                data={}, 
                raw_response=Mock(spec=httpx.Response)
            )

    dummy = DummyClass()
    
    with pytest.raises(Exception, match="Max retries reached"):
        dummy.transient_failure_method()

    # Ensure that the method retried the maximum number of times
    assert dummy.attempt_count == 3


def test_hybrid_retry_decorator_success_after_retries():
    class DummyClass:
        def __init__(self):
            self.attempt_count = 0

        @hybrid_retry_decorator(
                max_retries=4,  # Allows for 4 retries
                initial_wait_time=0.1, 
                initial_exponential_factor=1, 
                initial_retries=4, 
                fixed_interval=0.1
        )
        def method_with_retries(self):
            # Fail twice before succeeding
            if self.attempt_count < 2:
                self.attempt_count += 1
                raise httpx.ConnectError("Transient connection error")

            return SierraAPIResponse(
                response_model_name="Dummy", 
                data={}, 
                raw_response=Mock(spec=httpx.Response)
            )

    dummy = DummyClass()
    result = dummy.method_with_retries()

    # Ensure that the method eventually succeeded
    assert isinstance(result, SierraAPIResponse)
    # Ensure that the method retried the correct number of times
    assert dummy.attempt_count == 2


