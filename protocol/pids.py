"""
Definitii pentru PID-urile OBD-II (mode 01 - "current data").

Standardul SAE J1979 defineste PID-uri pe 2 caractere hex, fiecare cu un
numar fix de octeti de raspuns si o formula de conversie in valoare fizica
(A, B = primul, al doilea octet de date din raspuns, in ordinea primita).

Am ales primele 8 PID-uri care acopera un dashboard util si care sunt
suportate practic de orice ECU post-2001 (OBD-II e obligatoriu in UE
din 2001 pentru benzina / 2004 pentru diesel).
"""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class PidDefinition:
    pid: str
    name: str
    num_bytes: int
    formula: Callable[..., float]
    unit: str
    value_range: tuple[float, float]


PID_MAP: dict[str, PidDefinition] = {
    "0C": PidDefinition(
        pid="0C",
        name="RPM",
        num_bytes=2,
        formula=lambda a, b: ((a * 256) + b) / 4,
        unit="rpm",
        value_range=(0, 8000),
    ),
    "0D": PidDefinition(
        pid="0D",
        name="Viteza",
        num_bytes=1,
        formula=lambda a: a,
        unit="km/h",
        value_range=(0, 240),
    ),
    "05": PidDefinition(
        pid="05",
        name="Temp. lichid racire",
        num_bytes=1,
        formula=lambda a: a - 40,
        unit="C",
        value_range=(-40, 150),
    ),
    "04": PidDefinition(
        pid="04",
        name="Sarcina motor",
        num_bytes=1,
        formula=lambda a: a * 100 / 255,
        unit="%",
        value_range=(0, 100),
    ),
    "11": PidDefinition(
        pid="11",
        name="Pozitie acceleratie",
        num_bytes=1,
        formula=lambda a: a * 100 / 255,
        unit="%",
        value_range=(0, 100),
    ),
    "0F": PidDefinition(
        pid="0F",
        name="Temp. aer admisie",
        num_bytes=1,
        formula=lambda a: a - 40,
        unit="C",
        value_range=(-40, 100),
    ),
    "42": PidDefinition(
        pid="42",
        name="Voltaj baterie",
        num_bytes=2,
        formula=lambda a, b: ((a * 256) + b) / 1000,
        unit="V",
        value_range=(0, 18),
    ),
    "2F": PidDefinition(
        pid="2F",
        name="Nivel combustibil",
        num_bytes=1,
        formula=lambda a: a * 100 / 255,
        unit="%",
        value_range=(0, 100),
    ),
    "0A": PidDefinition(
        pid="0A",
        name="Presiune combustibil",
        num_bytes=1,
        formula=lambda a: a * 3,
        unit="kPa",
        value_range=(0, 765),
    ),
    "0B": PidDefinition(
        pid="0B",
        name="Presiune admisie",
        num_bytes=1,
        formula=lambda a: a,
        unit="kPa",
        value_range=(0, 255),
    ),
    "0E": PidDefinition(
        pid="0E",
        name="Avans aprindere",
        num_bytes=1,
        formula=lambda a: a / 2 - 64,
        unit="deg",
        value_range=(-64, 63.5),
    ),
    "14": PidDefinition(
        pid="14", name="Sonda O2 B1S1", num_bytes=2,
        formula=lambda a, b: a / 200,
        unit="V", value_range=(0, 1.275),
    ),
    "15": PidDefinition(
        pid="15", name="Sonda O2 B1S2", num_bytes=2,
        formula=lambda a, b: a / 200,
        unit="V", value_range=(0, 1.275),
    ),
    "16": PidDefinition(
        pid="16", name="Sonda O2 B1S3", num_bytes=2,
        formula=lambda a, b: a / 200,
        unit="V", value_range=(0, 1.275),
    ),
    "17": PidDefinition(
        pid="17", name="Sonda O2 B1S4", num_bytes=2,
        formula=lambda a, b: a / 200,
        unit="V", value_range=(0, 1.275),
    ),
    "18": PidDefinition(
        pid="18", name="Sonda O2 B2S1", num_bytes=2,
        formula=lambda a, b: a / 200,
        unit="V", value_range=(0, 1.275),
    ),
    "19": PidDefinition(
        pid="19", name="Sonda O2 B2S2", num_bytes=2,
        formula=lambda a, b: a / 200,
        unit="V", value_range=(0, 1.275),
    ),
    "1A": PidDefinition(
        pid="1A", name="Sonda O2 B2S3", num_bytes=2,
        formula=lambda a, b: a / 200,
        unit="V", value_range=(0, 1.275),
    ),
    "1B": PidDefinition(
        pid="1B", name="Sonda O2 B2S4", num_bytes=2,
        formula=lambda a, b: a / 200,
        unit="V", value_range=(0, 1.275),
    ),
    "06": PidDefinition(
        pid="06",
        name="Fuel trim scurt B1",
        num_bytes=1,
        formula=lambda a: (a - 128) * 100 / 128,
        unit="%",
        value_range=(-100, 99.2),
    ),
    "07": PidDefinition(
        pid="07",
        name="Fuel trim lung B1",
        num_bytes=1,
        formula=lambda a: (a - 128) * 100 / 128,
        unit="%",
        value_range=(-100, 99.2),
    ),
    "08": PidDefinition(
        pid="08",
        name="Fuel trim scurt B2",
        num_bytes=1,
        formula=lambda a: (a - 128) * 100 / 128,
        unit="%",
        value_range=(-100, 99.2),
    ),
    "09": PidDefinition(
        pid="09",
        name="Fuel trim lung B2",
        num_bytes=1,
        formula=lambda a: (a - 128) * 100 / 128,
        unit="%",
        value_range=(-100, 99.2),
    ),
    "10": PidDefinition(
        pid="10",
        name="Debit aer MAF",
        num_bytes=2,
        formula=lambda a, b: ((a * 256) + b) / 100,
        unit="g/s",
        value_range=(0, 655.35),
    ),
    "1F": PidDefinition(
        pid="1F",
        name="Timp functionare motor",
        num_bytes=2,
        formula=lambda a, b: (a * 256) + b,
        unit="s",
        value_range=(0, 65535),
    ),
    "21": PidDefinition(
        pid="21",
        name="Distanta cu MIL",
        num_bytes=2,
        formula=lambda a, b: (a * 256) + b,
        unit="km",
        value_range=(0, 65535),
    ),
    "33": PidDefinition(
        pid="33",
        name="Presiune atmosferica",
        num_bytes=1,
        formula=lambda a: a,
        unit="kPa",
        value_range=(0, 255),
    ),
    "52": PidDefinition(
        pid="52",
        name="Nivel etanol",
        num_bytes=1,
        formula=lambda a: a * 100 / 255,
        unit="%",
        value_range=(0, 100),
    ),
    "5C": PidDefinition(
        pid="5C",
        name="Temperatura ulei motor",
        num_bytes=1,
        formula=lambda a: a - 40,
        unit="C",
        value_range=(-40, 215),
    ),
    "5D": PidDefinition(
        pid="5D",
        name="Temperatura transmisie",
        num_bytes=1,
        formula=lambda a: a - 40,
        unit="C",
        value_range=(-40, 215),
    ),
    "62": PidDefinition(
        pid="62",
        name="Cuplu motor estimat",
        num_bytes=2,
        formula=lambda a, b: ((a * 256) + b) / 2 - 125,
        unit="%",
        value_range=(-125, 32767.5),
    ),
}

DEFAULT_POLL_ORDER = [
    "0C", "0D", "05", "04", "11", "0F", "42", "2F",
    "0B", "10", "0E", "06", "07", "08", "09", "0A",
    "14", "15", "16", "17", "18", "19", "1A", "1B",
    "1F", "21", "5C", "33", "52", "62", "5D",
]
