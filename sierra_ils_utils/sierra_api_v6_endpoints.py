from __future__ import annotations
from typing import Optional, List, Dict, Union
from pydantic import BaseModel

class Bib(BaseModel):
    id: str
    updatedDate: Optional[str]
    createdDate: Optional[str]
    deletedDate: Optional[str]
    deleted: bool
    suppressed: Optional[bool]
    available: Optional[bool]
    lang: Optional[Language]
    title: Optional[str]
    author: Optional[str]
    marc: Optional[Marc]
    materialType: Optional[MaterialType]
    bibLevel: Optional[BibLevel]
    publishYear: Optional[int]
    catalogDate: Optional[str]
    country: Optional[Country]
    orders: List[OrderInfo]
    normTitle: Optional[str]
    normAuthor: Optional[str]
    locations: List[Location]
    holdCount: Optional[int]
    copies: Optional[int]
    callNumber: Optional[str]
    volumes: Optional[List[str]]
    items: Optional[List[str]]
    fixedFields: Dict[int, FixedField]
    varFields: List[VarField]

class BibLevel(BaseModel):
    code: str
    value: Optional[str]

class BibResultSet(BaseModel):
    total: Optional[int]
    start: Optional[int]
    entries: List[Bib]

class Country(BaseModel):
    code: str
    name: str

class ErrorCode(BaseModel):
    code: int
    specificCode: int
    httpStatus: int
    name: str
    description: Optional[str]

class FieldData(BaseModel):
    subfields: List[MarcSubField]
    ind1: str
    ind2: str

class FixedField(BaseModel):
    label: str
    value: Optional["FixedFieldVal"]
    display: Optional[str]

class FixedFieldVal(BaseModel):
    value: Union[str, bool, int, float]

class Language(BaseModel):
    code: str
    name: Optional[str]

class Location(BaseModel):
    code: str
    name: str

class Marc(BaseModel):
    leader: str
    fields: List[MarcField]

class MarcField(BaseModel):
    tag: str
    value: Optional[str]
    data: Optional[FieldData]

class MarcSubField(BaseModel):
    code: str
    data: str

class MaterialType(BaseModel):
    code: str
    value: Optional[str]

class OrderInfo(BaseModel):
    orderId: str
    location: "Location"
    copies: int
    date: Optional[str]

class SubField(BaseModel):
    tag: str
    content: str

class TokenInfo(BaseModel):
    patronId: Optional[str]
    keyId: str
    grantType: Optional[str]
    authorizationScheme: str
    expiresIn: int
    roles: List[TokenInfoRole]

class TokenInfoRole(BaseModel):
    name: str
    tokenLifetime: int
    permissions: List[str]

class VarField(BaseModel):
    fieldTag: str
    marcTag: Optional[str]
    ind1: Optional[str]
    ind2: Optional[str]
    content: Optional[str]
    subfields: Optional[List[SubField]]


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
            "model": BibResultSet
        },
        "info/token": {
            # "path": "info/token",
            "responses": {
                200: TokenInfo
            },
            "model": TokenInfo
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
            "model": ErrorCode
        }
    }
}