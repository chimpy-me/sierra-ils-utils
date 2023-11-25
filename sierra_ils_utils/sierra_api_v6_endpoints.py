from __future__ import annotations
from datetime import date, datetime, timedelta
import json
from pydantic import BaseModel, validator # field_validator
import pymarc
from pymarc import Record  # using the Record object in the Bib object
from io import StringIO
from typing import List, Optional, Union, Dict

class DateOnlyRange(BaseModel):
    exact: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # @field_validator("exact", "start", "end")
    @validator('start', 'end', pre=True)
    def parse_to_date(cls, v):
        if not v:
            return None
        return date.fromisoformat(v).isoformat()
    
    # @field_validator("start_date")
    @validator('start_date', pre=True)
    def assign_start_date(cls, v, values):
        if "start" in values:
            return date.fromisoformat(values['start'])
        return None
    
    # @field_validator("end_date")
    @validator('end_date', pre=True)
    def assign_end_date(cls, v, values):
        if "end" in values:
            return date.fromisoformat(values['end'])
        return None
    
    def format_for_api(self) -> str:
        # If exact date is provided, return it
        if self.exact:
            return self.exact

        # If both start and end are the same, return the exact date
        if self.start and self.end and self.start == self.end:
            return self.start

        # If only start is provided
        if self.start and not self.end:
            return f"[{self.start},]"

        # If only end is provided
        if not self.start and self.end:
            return f"[,{self.end}]"

        # If both start and end are provided
        if self.start and self.end:
            return f"[{self.start},{self.end}]"

        # If neither start nor end is provided, return an empty string
        return ""

DateOnlyRange.update_forward_refs()


class DateRange(BaseModel):
    exact: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    
    # @field_validator("exact", "start", "end")
    @validator('start', 'end', pre=True)
    def parse_to_datetime(cls, v):
        if not v:
            return None
        try:
            return datetime.strptime(v, '%Y-%m-%dT%H:%M:%SZ').isoformat()
        except ValueError:
            # If that fails, try parsing as date
            parsed_date = date.fromisoformat(v)
            return datetime(parsed_date.year, parsed_date.month, parsed_date.day).isoformat()
    
    # @field_validator("start_datetime")
    @validator('start_datetime', pre=True)
    def assign_start_datetime(cls, v, values):
        if "start" in values:
            return datetime.fromisoformat(values['start'])
        return None
    
    # @field_validator("end_datetime")
    @validator('end_datetime', pre=True)
    def assign_end_datetime(cls, v, values):
        if "end" in values:
            return datetime.fromisoformat(values['end'])
        return None
    
    def delta(self) -> Optional[timedelta]:
        if self.start_datetime and self.end_datetime:
            return self.end_datetime - self.start_datetime
        return None
    
    def format_for_api(self) -> str:
        # If exact date is provided, return it
        if self.exact:
            return self.exact

        # If both start and end are the same, return the exact date or datetime
        if self.start and self.end and self.start == self.end:
            return self.start

        # If only start is provided
        if self.start and not self.end:
            return f"[{self.start},]"

        # If only end is provided
        if not self.start and self.end:
            return f"[,{self.end}]"

        # If both start and end are provided
        if self.start and self.end:
            return f"[{self.start},{self.end}]"

        # If neither start nor end is provided, return an empty string
        return ""

DateRange.update_forward_refs()


# id or id range for get params
class IdRange(BaseModel):
    start: Optional[int] = None
    end: Optional[int] = None
    
    def format_for_api(self):
        # If both start and end are the same, return exact id
        if self.start is not None and self.end is not None and self.start == self.end:
            return str(self.start)
        
        return f"[{self.start or ''},{self.end or ''}]"

IdRange.update_forward_refs()


class Language(BaseModel):
    code: str
    name: Optional[str] = None

Language.update_forward_refs()


class FixedFieldVal(BaseModel):
    value: Union[str, bool, int, float]

FixedFieldVal.update_forward_refs()


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

SubField.update_forward_refs()


class FieldData(BaseModel):
    subfields: List[SubField]
    ind1: str
    ind2: str

FieldData.update_forward_refs()


class MaterialType(BaseModel):
    code: str
    value: Optional[str] = None

MaterialType.update_forward_refs()


class BibLevel(BaseModel):
    code: str
    value: Optional[str] = None

BibLevel.update_forward_refs()


class Country(BaseModel):
    code: str
    name: str

Country.update_forward_refs()


class Location(BaseModel):
    code: str
    name: str

Location.update_forward_refs()


class OrderInfo(BaseModel):
    orderId: str
    location: "Location"
    copies: int
    date: Optional[str] = None

OrderInfo.update_forward_refs()


class VarField(BaseModel):
    fieldTag: str
    marcTag: Optional[str] = None
    ind1: Optional[str] = None
    ind2: Optional[str] = None
    content: Optional[str] = None
    subfields: Optional[List[SubField]] = None

VarField.update_forward_refs()


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
            
            # use JSONReader to read the marc Dict as a string
            reader = pymarc.reader.JSONReader(
                json.dumps(v)  # Convert the dict to a JSON string
            )
            record = next(reader.__iter__())  # Get the first record from the iterator

            return record
        return v
    
    class Config:
        arbitrary_types_allowed = True  # so we can use pymarc for the bib "Record" object

Bib.update_forward_refs()


class BibResultSet(BaseModel):
    total: Optional[int] = None
    start: Optional[int] = None
    entries: List[Bib]

BibResultSet.update_forward_refs()


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

Checkout.update_forward_refs()


class CheckoutResultSet(BaseModel):
    total: Optional[int] = None
    start: Optional[int] = None
    entries: List[Checkout]

CheckoutResultSet.update_forward_refs()


class ErrorCode(BaseModel):
    code: int
    specificCode: int
    httpStatus: int
    name: str
    description: Optional[str] = None

ErrorCode.update_forward_refs()


class ItemStatus(BaseModel):
    code: Optional[str] = None
    display: Optional[str] = None
    duedate: Optional[str] = None  # may want to use a datetime type if we want to parse the date

ItemStatus.update_forward_refs()


class ItemTransitInfo(BaseModel):
    to: Location
    forHold: bool

ItemTransitInfo.update_forward_refs()


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

Item.update_forward_refs()


class ItemResultSet(BaseModel):
    total: Optional[int] = None
    start: Optional[int] = None
    entries: List[Item]

ItemResultSet.update_forward_refs()


class TokenInfoRole(BaseModel):
    name: str
    tokenLifetime: int
    permissions: List[str]

TokenInfoRole.update_forward_refs()


class TokenInfo(BaseModel):
    # patronId: Optional[str]
    patronId: Optional[str] = None
    keyId: str
    grantType: Optional[str] = None
    authorizationScheme: str
    expiresIn: int
    roles: List[TokenInfoRole]

TokenInfo.update_forward_refs()


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

Volume.update_forward_refs()


class VolumeResultSet(BaseModel):
    total: Optional[int] = None
    start: Optional[int] = None
    entries: List[Volume]

VolumeResultSet.update_forward_refs()


# endpoints by HTTP verbs and paths for those verbs
endpoints = {
    "GET": {
        "bibs/": {
            "responses": {
                200: BibResultSet,
                400: ErrorCode,
                404: ErrorCode
                # ... other potential status codes and their corresponding models
            },
            "response_model": BibResultSet
        },
        "info/token": {
            # "path": "info/token",
            "responses": {
                200: TokenInfo
            },
            "response_model": TokenInfo
        },
        "items/": {
            "description": "Get a List of Item Records",
            "responses": {
                200: ItemResultSet,
                400: ErrorCode,
                404: ErrorCode
            },
            'response_model': ItemResultSet
        },
        "items/{id}": {
            "description": "Get an item by record ID",
            "responses": {
                200: Item,
                400: ErrorCode,
                404: ErrorCode
            },
            'response_model': Item
        },
        "items/checkouts": {
            "responses": {
                200: CheckoutResultSet,
                400: ErrorCode,
                404: ErrorCode
            },
            'response_model': CheckoutResultSet
        },
        "volumes/": {
            "responses": {
                200: VolumeResultSet,
                400: ErrorCode,
                404: ErrorCode
            }
        }, 
        "volumes/{id}": {
            "responses": {
                200: Volume,
                400: ErrorCode,
                404: ErrorCode
            },
            "response_model": Volume
        }
    },
    "DELETE": {
        "bibs/": {
            # "path": "bibs/",
            "responses": {
                200: None,
                204: None,
                400: ErrorCode,
                404: ErrorCode
            },
            "response_model": ErrorCode
        }
    }
}