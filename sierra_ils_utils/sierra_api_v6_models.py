from typing import Optional, List, Dict, Union

# Define the data models
class ErrorCode:
    code: int
    specificCode: int
    httpStatus: int
    name: str
    description: Optional[str]

class Language:
    code: str
    name: Optional[str]

class MarcSubField:
    code: str
    data: str

class FieldData:
    subfields: List[MarcSubField]
    ind1: str
    ind2: str

class MarcField:
    tag: str
    value: Optional[str]
    data: Optional[FieldData]

class Marc:
    leader: str
    fields: List[MarcField]

class MaterialType:
    code: str
    value: Optional[str]

class BibLevel:
    code: str
    value: Optional[str]

class Country:
    code: str
    name: str

class Location:
    code: str
    name: str

class OrderInfo:
    orderId: str
    location: Location
    copies: int
    date: Optional[str]

class FixedFieldVal:
    value: Union[str, bool, int, float]  # Assuming T can be one of these types

class FixedField:
    label: str
    value: Optional[FixedFieldVal]
    display: Optional[str]

class SubField:
    tag: str
    content: str

class VarField:
    fieldTag: str
    marcTag: Optional[str]
    ind1: Optional[str]
    ind2: Optional[str]
    content: Optional[str]
    subfields: Optional[List[SubField]]

class Bib:
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

class BibResultSet:
    total: Optional[int]
    start: Optional[int]
    entries: List[Bib]