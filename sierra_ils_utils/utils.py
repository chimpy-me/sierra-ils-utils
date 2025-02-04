from .sierra_rest_client import SierraRESTClient

import logging
from typing import Optional

# Module-level logger
logger = logging.getLogger(__name__)

def get_max_record_id(
    client: SierraRESTClient,  # SierraAPI or SierraRESTClient
    endpoint: str,
    start: int = 0,
    limit: int = 50,
    max_safety: int = 1_000_000_000
) -> int:
    """
    Find the maximum valid Record ID for which the API returns at least one entry.

    This will work on GET endpoints that support getting record result sets by 
    id range.

    Example Use:
        max_possible_id = get_max_record_id(client, 'patrons/', start=2_500_000)
        print("Max valid ID:", max_possible_id)  # e.g., 2707822

    This version handles both cases:
      - If 'start' yields entries, we assume it is below (or near) the maximum ID,
        and we perform an exponential (galloping) search upward to bracket the top,
        followed by a binary search.
      - If 'start' does not yield any entries, we perform a downward binary search 
        in the range [0, start].

    :param client:      A SierraRESTClient (or SierraAPI) instance.
    :param endpoint:    The GET API endpoint (e.g., 'patrons/').
    :param start:       The initial ID from which to begin searching (default=0).
    :param limit:       The number of items to request per call.
    :param max_safety:  A hard cap for 'high' to avoid infinite loops.
    :return:            The maximum ID (integer) that returns at least one entry.
    """

    requests_made = 0

    def get_entry_count(min_id: int) -> int:
        """
        Returns how many entries come back for records with ID >= min_id.
        Increments our request counter and logs the request number.
        """
        nonlocal requests_made
        requests_made += 1

        logger.debug(f"[Request #{requests_made}] Checking ID >= {min_id}")

        response = client.request(
            'GET',
            endpoint,
            params={
                'limit': limit,
                'fields': 'id',
                'id': f"[{min_id},]"
            }
        )
        response.raise_for_status()
        return len(response.json().get('entries', []))

    # 1) Check if 'start' yields any entries.
    initial_count = get_entry_count(start)
    logger.debug(f"Initial count at start={start}: {initial_count}")

    if initial_count > 0:
        # -----------------------------------------------------
        # CASE A: We have entries at 'start' => search upward
        # -----------------------------------------------------
        low = start
        high = max(start, 1)  # ensure we start at least at 1

        # 1A) EXPONENTIAL (GALLOPING) SEARCH UPWARD
        while high <= max_safety:
            count = get_entry_count(high)
            logger.debug(f"Exponential up -> low={low}, high={high}, count={count}")

            if count == 0:  # Only break when no entries are returned
                break

            low = high
            high *= 2
            if high > max_safety:
                logger.debug(f"Hit max_safety={max_safety}; capping exponential search.")
                high = max_safety
                break

        # 1B) BINARY SEARCH in [low, high]
        max_valid = low
        logger.debug(f"Binary search upward -> low={low}, high={high}")

        while low <= high:
            mid = (low + high) // 2
            count = get_entry_count(mid)
            logger.debug(f"Binary up -> low={low}, mid={mid}, high={high}, count={count}")

            if count == 0:
                high = mid - 1
            else:
                max_valid = mid
                low = mid + 1

        logger.info(
            f"Found max_valid={max_valid} with {requests_made} total requests (start={start}, upward)."
        )
        return max_valid

    else:
        # -----------------------------------------------------
        # CASE B: We overshot => do a downward binary search in [0..start]
        # -----------------------------------------------------
        logger.info(f"No entries at start={start}; searching downward [0..{start}]")

        low = 0
        high = start
        max_valid = 0

        while low <= high:
            mid = (low + high) // 2
            count = get_entry_count(mid)
            logger.debug(f"Binary down -> low={low}, mid={mid}, high={high}, count={count}")

            if count == 0:
                high = mid - 1
            else:
                max_valid = mid
                low = mid + 1

        logger.info(
            f"Found max_valid={max_valid} with {requests_made} total requests (start={start}, downward)."
        )
        return max_valid
