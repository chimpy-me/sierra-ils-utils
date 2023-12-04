import pytest
from sierra_ils_utils import Models
import json

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_validate_PatronResultSet():
    with open('./tests/patrons-1.json') as f:
        data = json.load(f)

    patrons = Models.PatronResultSet.validate(data)
    assert patrons is not None