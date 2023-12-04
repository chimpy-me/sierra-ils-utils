
from .sierra_ils_utils import SierraRESTAPI, JsonManipulator, SierraQueryBuilder
from .sierra_api_v6_endpoints import endpoints
# from .sierra_api_v6_endpoints import Bib, BibResultSet, Item, ItemResultSet, RecordDateRange, Patron, PatronResultSet
from .sierra_api_v6_endpoints import *

import inspect
import logging
from pydantic import BaseModel
import sys

logger = logging.getLogger(__name__)
logger.debug(f'INIT')
# logger.debug(f'INIT: sys.modules: {sys.modules}')

# create aliases ...
SierraAPI = SierraRESTAPI
QueryBuilder = SierraQueryBuilder

# create a namespace for our models

class Models:
    pass

# Dynamically add all Pydantic models to the Models class
module_name = 'sierra_ils_utils.sierra_api_v6_endpoints'
for name, obj in inspect.getmembers(sys.modules[module_name]):
    if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
        setattr(Models, name, obj)


# Usage Example:
# bib_model = Models.Bib(...)

# ... so they can be imported like from sierra_ils_utils import Models
# class Models(BaseModel):
#     Bib: Bib
#     BibResultSet: BibResultSet
#     Item: Item
#     ItemResultSet: ItemResultSet
#     RecordDateRange: RecordDateRange
#     Patron: Patron
#     PatronResultSet: PatronResultSet

#     class Config:
#         arbitrary_types_allowed = True