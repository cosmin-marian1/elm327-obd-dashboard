"""Decodare locala a informatiilor standard disponibile intr-un VIN."""

from datetime import datetime


_COUNTRIES = {
    "1": "SUA", "2": "Canada", "3": "Mexic", "4": "SUA", "5": "SUA",
    "J": "Japonia", "K": "Coreea de Sud", "L": "China", "M": "India",
    "N": "Turcia", "S": "Marea Britanie", "T": "Elvetia/Ungaria",
    "V": "Franta/Spania", "W": "Germania", "X": "Rusia",
    "Y": "Suedia/Finlanda", "Z": "Italia",
}

_MANUFACTURERS = {
    "MAT": "Tata Motors",
    "WP0": "Porsche",
    "WVW": "Volkswagen",
    "WBA": "BMW",
    "WDB": "Mercedes-Benz",
    "WDD": "Mercedes-Benz",
    "VF1": "Renault",
    "VSY": "Iveco",
    "JHM": "Honda",
    "JTD": "Toyota",
    "KMH": "Hyundai",
}

_YEAR_CODES = "ABCDEFGHJKLMNPRSTVWXY"


def _model_years(code: str) -> str:
    if code not in _YEAR_CODES:
        return "necunoscut"
    base_year = 1980 + _YEAR_CODES.index(code)
    current_year = datetime.now().year
    candidates = [year for year in range(base_year, current_year + 31, 30)
                  if current_year - 30 <= year <= current_year]
    return "/".join(str(year) for year in candidates)


def decode_vin(vin: str) -> dict[str, str]:
    """Intoarce informatiile standard care pot fi extrase fara o baza externa."""
    normalized = vin.strip().upper()
    wmi = normalized[:3]
    return {
        "producator": _MANUFACTURERS.get(wmi, f"necunoscut ({wmi})"),
        "tara": _COUNTRIES.get(normalized[0], "necunoscuta"),
        "an_model": _model_years(normalized[9]),
        "fabrica": normalized[10],
        "serie": normalized[11:],
        "model": "indisponibil din VIN standard",
    }
