from __future__ import annotations
from typing import List, Optional, Union  # Literal
from pydantic import BaseModel, field_validator
from datetime import date, datetime, timedelta 

class DateOnlyRange(BaseModel):
    exact: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    @field_validator("exact", "start", "end")
    def parse_to_date(cls, v):
        if not v:
            return None
        return date.fromisoformat(v).isoformat()
    
    @field_validator("start_date")
    def assign_start_date(cls, v, values):
        if "start" in values:
            return date.fromisoformat(values['start'])
        return None
    
    @field_validator("end_date")
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

class DateRange(BaseModel):
    exact: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    
    @field_validator("exact", "start", "end")
    def parse_to_datetime(cls, v):
        if not v:
            return None
        try:
            return datetime.strptime(v, '%Y-%m-%dT%H:%M:%SZ').isoformat()
        except ValueError:
            # If that fails, try parsing as date
            parsed_date = date.fromisoformat(v)
            return datetime(parsed_date.year, parsed_date.month, parsed_date.day).isoformat()
    
    @field_validator("start_datetime")
    def assign_start_datetime(cls, v, values):
        if "start" in values:
            return datetime.fromisoformat(values['start'])
        return None
    
    @field_validator("end_datetime")
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

# id or id range for get params
class IdRange(BaseModel):
    start: Optional[int] = None
    end: Optional[int] = None
    
    def format_for_api(self):
        # If both start and end are the same, return exact id
        if self.start is not None and self.end is not None and self.start == self.end:
            return str(self.start)
        
        return f"[{self.start or ''},{self.end or ''}]"

class Bib(BaseModel):
    id: str
    updatedDate: Optional[str] = None
    createdDate: Optional[str] = None
    deletedDate: Optional[str] = None
    deleted: bool
    suppressed: Optional[bool] = None
    available: Optional[bool] = None
    lang: Optional[Language] = None
    title: Optional[str] = None
    author: Optional[str] = None
    marc: Optional[Marc] = None
    materialType: Optional[MaterialType] = None
    bibLevel: Optional[BibLevel] = None
    publishYear: Optional[int] = None
    catalogDate: Optional[str] = None
    country: Optional[Country] = None
    orders: List[OrderInfo]
    normTitle: Optional[str] = None
    normAuthor: Optional[str] = None
    locations: List[Location]
    holdCount: Optional[int] = None
    copies: Optional[int] = None
    callNumber: Optional[str] = None
    volumes: Optional[List[str]] = None
    items: Optional[List[str]] = None
    fixedFields: Dict[int, FixedField]
    varFields: List[VarField]

class BibLevel(BaseModel):
    code: str
    value: Optional[str] = None

class BibResultSet(BaseModel):
    total: Optional[int] = None
    start: Optional[int] = None
    entries: List[Bib]

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

class Country(BaseModel):
    code: str
    name: str

class ErrorCode(BaseModel):
    code: int
    specificCode: int
    httpStatus: int
    name: str
    description: Optional[str] = None

class FieldData(BaseModel):
    subfields: List[MarcSubField]
    ind1: str
    ind2: str

class FixedField(BaseModel):
    label: str
    value: Optional["FixedFieldVal"] = None
    display: Optional[str] = None

class FixedFieldVal(BaseModel):
    value: Union[str, bool, int, float]

class Item(BaseModel):
    id: str
    updatedDate: Optional[str] = None
    createdDate: Optional[str] = None
    deletedDate: Optional[str] = None
    deleted: bool
    suppressed: bool
    bibIds: List[str]
    location: Optional[Location] = None
    status: Optional[ItemStatus] = None
    volumes: Optional[List[str]] = None
    barcode: Optional[str] = None
    callNumber: Optional[str] = None
    itemType: Optional[str] = None
    transitInfo: Optional[ItemTransitInfo] = None
    copyNo: Optional[int] = None
    holdCount: Optional[int] = None
    fixedFields: Dict[int, FixedField]
    varFields: List[VarField]

class ItemResultSet(BaseModel):
    total: Optional[int] = None
    start: Optional[int] = None
    entries: List[Item]

class ItemStatus(BaseModel):
    code: Optional[str] = None
    display: Optional[str] = None
    duedate: Optional[str] = None  # may want to use a datetime type if we want to parse the date

class ItemTransitInfo(BaseModel):
    to: Location
    forHold: bool

class Language(BaseModel):
    code: str
    name: Optional[str] = None

class Location(BaseModel):
    code: str
    name: str

class Marc(BaseModel):
    leader: str
    fields: List[MarcField]

class MarcField(BaseModel):
    tag: str
    value: Optional[str] = None
    data: Optional[FieldData] = None

class MarcSubField(BaseModel):
    code: str
    data: str

class MaterialType(BaseModel):
    code: str
    value: Optional[str] = None

class OrderInfo(BaseModel):
    orderId: str
    location: "Location"
    copies: int
    date: Optional[str] = None

class SubField(BaseModel):
    tag: str
    content: str

class TokenInfo(BaseModel):
    # patronId: Optional[str]
    patronId: Optional[str] = None
    keyId: str
    grantType: Optional[str] = None
    authorizationScheme: str
    expiresIn: int
    roles: List[TokenInfoRole]

class TokenInfoRole(BaseModel):
    name: str
    tokenLifetime: int
    permissions: List[str]

class VarField(BaseModel):
    fieldTag: str
    marcTag: Optional[str] = None
    ind1: Optional[str] = None
    ind2: Optional[str] = None
    content: Optional[str] = None
    subfields: Optional[List[SubField]] = None

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