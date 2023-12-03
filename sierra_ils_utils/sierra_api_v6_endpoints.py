from __future__ import annotations
from datetime import date, datetime, timedelta
import logging
import json
from pydantic import BaseModel, validator # field_validator
from pymarc import Record, JSONReader, MARCWriter  # using the Record object in the Bib object
from io import StringIO, BufferedIOBase
from typing import List, Optional, Union, Dict, Tuple, Generator

# Set up the logger at the module level
logger = logging.getLogger(__name__)

class Version:
    """
    print the version info
    TODO: should this do more?
    """
    def __str__(self) -> str:
        return 'v6'


class RecordDateRange(BaseModel):
    """
    Date ranges are inclusive.
    dates can be provided as:
      - ISO 8601 strings (with or without 'Z')  e.g. '2023-11-01T00:00:00Z'
      - date-only strings                       e.g. '2023-11-01'
      - Unix epoch timestamps (integer)         e.g. 1669852800
    """
    start_date: Optional[Union[datetime, date]] = None
    end_date: Optional[Union[datetime, date]] = None
    exact_date: Optional[Union[datetime, date]] = None

    @validator('start_date', 'end_date', 'exact_date', pre=True)
    def parse_date(cls, v):
        if isinstance(v, (datetime, date)):
            return v
        if isinstance(v, (str, int, float)):
            try:
                if isinstance(v, str):
                    if 'T' in v:
                        # Parse as datetime
                        return datetime.fromisoformat(v.replace('Z', '+00:00'))
                    else:
                        # Parse as date
                        return datetime.strptime(v, '%Y-%m-%d').date()
                else:  # v is an int or float (Unix epoch)
                    return datetime.fromtimestamp(v)
            except ValueError:
                raise ValueError("Invalid date format")

        return None

    def advance_range(self, interval_str: str):
        """
        advance the range by a time interval:
        e.g. the previous end_date becomes the new start_date + 1 second (to prevent overlap), and the new end_date is advanced by the interval
        
        interval_str are these possible string values:
        'minutes=1', 
        'hours=1',
        'days=1',
        'weeks=1'
        """
        if not isinstance(self.start_date, datetime) or not isinstance(self.end_date, datetime):
            raise TypeError("start_date and end_date must be datetime objects")

        if not self.start_date or not self.end_date:
            raise ValueError("Both start_date and end_date must be set to advance the range")

        if interval_str:
            # Parse the provided interval string
            interval_parts = interval_str.split('=')
            if len(interval_parts) != 2:
                raise ValueError("Interval string must be in the format 'unit=value'")
            unit, value = interval_parts
            try:
                interval = timedelta(**{unit: int(value)})
            except (ValueError, TypeError):
                raise ValueError("Invalid interval string format or value")

        # Update start and end dates
        # ... need to advance the start date by 1 second so that we don't overlap
        # ... date ranges are inclusive
        self.start_date = self.end_date + timedelta(seconds=1)
        self.end_date += interval


    def format_for_api(self) -> str:
        def format_date(date_obj):
            if isinstance(date_obj, datetime):
                return date_obj.isoformat() + 'Z'
            elif isinstance(date_obj, date):
                return date_obj.isoformat()
            return ''

        # if exact date is set, return only that
        if self.exact_date:
            return format_date(self.exact_date)

        # otherwise, return the start and end dates in either [start_date,end_date] or [,end_date] or [start_date,]
        start = format_date(self.start_date) if self.start_date else ''
        end = format_date(self.end_date) if self.end_date else ''

        return f"[{start},{end}]"

    def __str__(self) -> str:
        return self.format_for_api()


class IdRange(BaseModel):
    start: Optional[int] = None
    end: Optional[int] = None
    
    def format_for_api(self):
        # If both start and end are the same, return exact id
        if self.start is not None and self.end is not None and self.start == self.end:
            return str(self.start)
        
        return f"[{self.start or ''},{self.end or ''}]"


class Language(BaseModel):
    code: str
    name: Optional[str] = None


class FixedFieldVal(BaseModel):
    value: Union[str, bool, int, float]


# class FixedField(BaseModel):
#     label: str
#     value: Optional["FixedFieldVal"] = None
#     display: Optional[str] = None
#
# FixedField.update_forward_refs()
FixedField = Dict  # for now, lets just treat this as a dict


class SubField(BaseModel):
    tag: str
    content: str


class FieldData(BaseModel):
    subfields: List[SubField]
    ind1: str
    ind2: str


class MaterialType(BaseModel):
    code: str
    value: Optional[str] = None


class BibLevel(BaseModel):
    code: str
    value: Optional[str] = None


class Country(BaseModel):
    code: str
    name: str


class Location(BaseModel):
    code: str
    name: str


class OrderInfo(BaseModel):
    orderId: str
    location: "Location"
    copies: int
    date: Optional[str] = None


class VarField(BaseModel):
    fieldTag: str
    marcTag: Optional[str] = None
    ind1: Optional[str] = None
    ind2: Optional[str] = None
    content: Optional[str] = None
    subfields: Optional[List[SubField]] = None


class Bib(BaseModel):
    id: str
    updatedDate: Optional[str] = None
    createdDate: Optional[str] = None
    deletedDate: Optional[str] = None
    deleted: Optional[bool] = None
    suppressed: Optional[bool] = None
    available: Optional[bool] = None
    lang: Optional[Language] = None
    title: Optional[str] = None
    author: Optional[str] = None
    materialType: Optional[MaterialType] = None
    bibLevel: Optional[BibLevel] = None
    publishYear: Optional[int] = None
    catalogDate: Optional[str] = None
    country: Optional[Country] = None
    orders: Optional[List[OrderInfo]] = None
    normTitle: Optional[str] = None
    normAuthor: Optional[str] = None
    locations: Optional[List[Location]] = None
    holdCount: Optional[int] = None
    copies: Optional[int] = None
    callNumber: Optional[str] = None
    volumes: Optional[List[str]] = None
    items: Optional[List[str]] = None
    # fixedFields: Optional[Dict[int, FixedField]] = None
    fixedFields: Optional[FixedField] = None
    varFields: Optional[List[VarField]] = None

    marc: Optional[Record] = None  # defining this as a pydantic model is a wide-awake nightmare
    @validator('marc', pre=True)
    def convert_dict_to_marc_record(cls, v):
        if v is not None and isinstance(v, Dict):
            
            # use the Pymarc JSONReader to read the marc Dict as a string
            # reader = pymarc.reader.JSONReader(
            reader = JSONReader(
                json.dumps(v)  # Convert the dict to a JSON string
            )
            record = next(reader.__iter__())  # Get the first record from the iterator

            return record
        return v
    
    class Config:
        arbitrary_types_allowed = True  # so we can use pymarc for the bib "Record" object


class BibResultSet(BaseModel):
    total: Optional[int] = None
    start: Optional[int] = None
    entries: List[Bib]

    # def serialize_marc_records(self, file_path: str) -> None:
    #     """Serializes all MARC records in the entries to a MARC file."""
    #     with open(file_path, 'wb') as file:
    #         writer = MARCWriter(file)
    #         for bib in self.entries:
    #             if bib.marc:
    #                 writer.write(bib.marc)
    def serialize_marc_records(self, file_or_path: Union[str, BufferedIOBase]) -> None:
        """Serializes all MARC records in the entries to a MARC file or file-like object."""
        close_file = False
        if isinstance(file_or_path, str):
            file = open(file_or_path, 'wb')
            close_file = True  # Only close the file if we opened it
        elif isinstance(file_or_path, BufferedIOBase):
            file = file_or_path
        else:
            raise ValueError("file_or_path must be a string or a file-like object")

        writer = MARCWriter(file)
        for bib in self.entries:
            if bib.marc:
                writer.write(bib.marc)
        
        if close_file:
            file.close()  # Close the file only if this method opened it


class Checkout(BaseModel):
    id: str
    patron: str
    item: str
    barcode: Optional[str] = None
    dueDate: Optional[str]  = None # may want to use a datetime type if we want to parse the date
    callNumber: Optional[str] = None
    numberOfRenewals: Optional[int] = None
    outDate: Optional[str] = None  # ...consider using datetime type for date parsing
    recallDate: Optional[str] = None  # ...consider using datetime type for date parsing


class CheckoutResultSet(BaseModel):
    total: Optional[int] = None
    start: Optional[int] = None
    entries: List[Checkout]


class ErrorCode(BaseModel):
    code: int
    specificCode: int
    httpStatus: int
    name: str
    description: Optional[str] = None


class ItemStatus(BaseModel):
    code: Optional[str] = None
    display: Optional[str] = None
    duedate: Optional[str] = None  # may want to use a datetime type if we want to parse the date


class ItemTransitInfo(BaseModel):
    to: Location
    forHold: bool


class Item(BaseModel):
    id: str
    updatedDate: Optional[str] = None
    createdDate: Optional[str] = None
    deletedDate: Optional[str] = None
    deleted: Optional[bool] = None
    suppressed: Optional[bool] = None
    bibIds: Optional[List[str]] = None
    location: Optional[Location] = None
    status: Optional[ItemStatus] = None
    volumes: Optional[List[str]] = None
    barcode: Optional[str] = None
    callNumber: Optional[str] = None
    itemType: Optional[str] = None
    transitInfo: Optional[ItemTransitInfo] = None
    copyNo: Optional[int] = None
    holdCount: Optional[int] = None
    # fixedFields: Optional[Dict[int, FixedField]] = None
    fixedFields: Optional[FixedField] = None
    varFields: Optional[List[VarField]] = None


class ItemResultSet(BaseModel):
    total: Optional[int] = None
    start: Optional[int] = None
    entries: List[Item]


class TokenInfoRole(BaseModel):
    name: str
    tokenLifetime: int
    permissions: List[str]


class TokenInfo(BaseModel):
    # patronId: Optional[str]
    patronId: Optional[str] = None
    keyId: str
    grantType: Optional[str] = None
    authorizationScheme: str
    expiresIn: int
    roles: List[TokenInfoRole]


# Volume Model
class Volume(BaseModel):
    id: int
    updatedDate: Optional[str] = None
    createdDate: Optional[str] = None
    deletedDate: Optional[str] = None
    deleted: bool
    holds: Optional[List[str]] = None
    volume: Optional[str] = None
    bibs: Optional[List[str]] = None
    items: Optional[List[str]] = None
    varFields: List[VarField] = None


class VolumeResultSet(BaseModel):
    total: Optional[int] = None
    start: Optional[int] = None
    entries: List[Volume]


class QueryEntry(BaseModel):
    link: str  # a link to the resulting record

    def get_id(self) -> Optional[int]:
        """
        Extracts the record type and ID from the link.

        Returns:
            A tuple of (record_type, record_id).
            If the pattern is not found or validations fail, (None, None) is returned.
        """
        # if we can't validate, then 
        record_id = None

        try:
            record_id = self.link.split('/')[-1]  # id is at the end of the uri path

            # Validate that record_id can be converted to an integer
            record_id = int(record_id)  # This will raise ValueError if record_id is not a valid integer string

        except Exception as e:
            logger.warn(f'Error: {e}')
            
        return record_id
    
    def get_record_type(self) -> Optional[str]:
        """
        Extracts the record type and ID from the link.

        Returns:
            A tuple of (record_type, record_id).
            If the pattern is not found or validations fail, (None, None) is returned.
        """
        # if we can't validate, then 
        record_type = None

        try:
            record_type = self.link.split('/')[-2]  # id is at the end of the uri path (before the id)

        except Exception as e:
            logger.warn(f'Error: {e}')
            
        return record_type


class QueryResultSet(BaseModel): 
    total: Optional[int] = None  # the total number of results,
    start: Optional[int] = None  # the starting position of this set
    entries: List[QueryEntry]    # the list of QueryEntry

    # @property
    # def entry_ids(self) -> Generator[int, None, None]:
    #     """
    #     TODO: not sure if i want to send a generator, or just a list
    #     Yields the IDs from all entries.

    #     Yields:
    #         Record IDs. If an ID is not found, it is skipped.
    #     """
    #     for entry in self.entries:
    #         _, entry_id = entry.get_id()
    #         if entry_id is not None:
    #             yield entry_id

    @property
    def entry_ids(self) -> List[int]:
        """
        Returns the IDs from all entries as a list.

        Returns:
            List of record IDs. If an ID is not found, it is skipped.
        """
        ids = []
        for entry in self.entries:
            entry_id = entry.get_id()
            if entry_id is not None:
                ids.append(entry_id)
        return ids

    @property
    def record_types(self) -> Optional[str]:
        """
        Extracts the record type from entries and checks if it is consistent.

        Returns:
            The record type if it is consistent across all entries, otherwise None.
        """
        if not self.entries:
            return None

        record_types = {entry.get_record_type() for entry in self.entries}  # create a set out of the types ...
        if len(record_types) == 1:                                          # should only be one ...
            return record_types.pop()                                       # return it
        else:
            logger.warning('Inconsistent record types found in entries.')
            return None


# Generic way to update forward references for all Pydantic models
model_classes = [obj for obj in globals().values() 
                 if isinstance(obj, type) and issubclass(obj, BaseModel)]
for model_class in model_classes:
    model_class.update_forward_refs()

"""
# 
# 
# Endpoints
#
#
"""

# endpoints by HTTP verbs and paths for those verbs
endpoints = {
    "GET": {
        "bibs/": {
            "responses": {
                200: BibResultSet,
                400: ErrorCode,
                404: ErrorCode,
                # ... other potential status codes and their corresponding models
            },
            "response_model": BibResultSet
        },
        "bibs/{id}": {
            "responses": {
                200: Bib,
                400: ErrorCode,
                404: ErrorCode,
            },
            "response_model": Bib
        },
        "info/token": {
            # "path": "info/token",
            "responses": {
                200: TokenInfo,
            },
            "response_model": TokenInfo
        },
        "items/": {
            "description": "Get a List of Item Records",
            "responses": {
                200: ItemResultSet,
                400: ErrorCode,
                404: ErrorCode,
            },
            'response_model': ItemResultSet
        },
        "items/{id}": {
            "description": "Get an item by record ID",
            "responses": {
                200: Item,
                400: ErrorCode,
                404: ErrorCode,
            },
            'response_model': Item
        },
        "items/checkouts": {
            "responses": {
                200: CheckoutResultSet,
                400: ErrorCode,
                404: ErrorCode,
            },
            'response_model': CheckoutResultSet
        },
        "volumes/": {
            "responses": {
                200: VolumeResultSet,
                400: ErrorCode,
                404: ErrorCode,
            }
        }, 
        "volumes/{id}": {
            "responses": {
                200: Volume,
                400: ErrorCode,
                404: ErrorCode,
            },
            "response_model": Volume
        }
    },
    "POST": {
        "bibs/query": {
            """
            Filter the records by a query in JSON format
            """
            "responses": {
                200: QueryResultSet,
                400: ErrorCode,
                404: ErrorCode,
            },
            "response_model": QueryResultSet,
            "body_required": True,
            "body_format": "json"
        },
        "items/query": {
            """
            Filter the records by a query in JSON format
            """
            "responses": {
                200: QueryResultSet,
                400: ErrorCode,
                404: ErrorCode,
            },
            "response_model": QueryResultSet,
            "body_required": True,
            "body_format": "json"
        },
    },
    "DELETE": {
        "bibs/{id}": {
            # "path": "bibs/",
            "responses": {
                200: None,
                204: None,
                400: ErrorCode,
                404: ErrorCode,
            },
            "response_model": ErrorCode
        }
    }
}
