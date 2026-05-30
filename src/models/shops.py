from dataclasses import dataclass


@dataclass
class VarusShop:
    id: int
    tms_id: str
    short_name: str
    lat: float
    lon: float
    address: str

@dataclass
class ATBShop:
    id: int
    short_name: str
    lat: float
    lon: float
    address: str
    worktime: str

@dataclass
class ForaShop:
    id: int
    short_name: str
    lat: float
    lon: float
    address: str
