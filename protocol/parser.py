"""
Parsare raspunsuri brute de la ELM327.
Raspuns tipic la un PID (echo oprit cu ATE0):  "41 0C 1A F8"
"""

from protocol.pids import PID_MAP, PidDefinition

ELM_ERROR_RESPONSES = {
    "NO DATA", "UNABLE TO CONNECT", "?", "STOPPED", "ERROR",
    "BUS INIT: ERROR", "CAN ERROR",
}


class ParseError(Exception):
    """Raspuns invalid sau eroare raportata de ELM327."""


def clean_response(raw: str) -> str:
    """Scoate CR/LF, promptul '>', 'SEARCHING...' si spatiile in exces."""
    cleaned = raw.replace("\r", " ").replace("\n", " ").replace(">", "")
    cleaned = cleaned.replace("SEARCHING...", " ")
    return " ".join(cleaned.split())


def parse_vin_response(raw_response: str) -> str:
    """Decodeaza raspunsul multi-linie la mode 09 PID 02."""
    lines = raw_response.replace("\r", "\n").replace(">", "").splitlines()
    chunks: dict[int, list[int]] = {}
    for line in lines:
        line = line.replace("SEARCHING...", " ").strip()
        frame_prefix = None
        if ":" in line and line.split(":", 1)[0].strip().isdigit():
            prefix, line = line.split(":", 1)
            frame_prefix = int(prefix.strip())
        tokens = line.split()
        response_start = next(
            (index for index in range(len(tokens) - 1)
             if tokens[index].upper() == "49" and tokens[index + 1].upper() == "02"),
            None,
        )
        if response_start is not None:
            data_start = response_start + 3
            sequence = frame_prefix if frame_prefix is not None else int(tokens[response_start + 2], 16)
        elif frame_prefix is not None:
            data_start = 0
            sequence = frame_prefix
        else:
            continue
        try:
            data = [int(token, 16) for token in tokens[data_start:]]
        except ValueError:
            continue
        chunks[sequence] = data

    if not chunks:
        raise ParseError("Raspuns VIN indisponibil: '{0}'".format(clean_response(raw_response)))

    try:
        vin = "".join(chr(byte) for sequence in sorted(chunks) for byte in chunks[sequence])
    except ValueError as exc:
        raise ParseError("Octeti invalizi in raspunsul VIN") from exc
    vin = vin.replace("\x00", "").replace("\r", "").replace("\n", "").strip()
    if len(vin) < 17 or not vin[:17].isalnum():
        raise ParseError(f"VIN invalid: '{vin}'")
    return vin[:17]

def parse_supported_pids_response(raw_response: str, base_pid: int) -> set[str]:
    """
    Parseaza raspunsul la o interogare de bitmap: "41 00 XX XX XX XX".
    Cei 4 octeti de date = 32 de biti; bitul i (de la 1) setat inseamna ca
    PID-ul (base_pid + i) e suportat. Ultimul bit indica daca exista si
    blocul urmator (0100 -> 0120 -> 0140...).
    """
    cleaned = clean_response(raw_response).upper()
    tokens = cleaned.split()
    expected = f"{base_pid:02X}"
    if len(tokens) < 6 or tokens[0] != "41" or tokens[1] != expected:
        raise ParseError(f"Raspuns neasteptat pentru bitmap {expected}: '{cleaned}'")

    data = tokens[2:6]
    try:
        bits = "".join(f"{int(b, 16):08b}" for b in data)
    except ValueError as exc:
        raise ParseError(f"Octeti invalizi in bitmap: '{cleaned}'") from exc

    return {f"{base_pid + i:02X}" for i, bit in enumerate(bits, start=1) if bit == "1"}

def parse_pid_response(pid: str, raw_response: str) -> float:
    cleaned = clean_response(raw_response).upper()

    if any(err in cleaned for err in ELM_ERROR_RESPONSES):
        raise ParseError(f"ELM327 a raspuns cu eroare: '{cleaned}'")

    tokens = cleaned.split()
    if len(tokens) < 2 or tokens[0] != "41" or tokens[1] != pid:
        raise ParseError(f"Raspuns neasteptat pentru PID {pid}: '{cleaned}'")

    pid_def: PidDefinition | None = PID_MAP.get(pid)
    if pid_def is None:
        raise ParseError(f"PID {pid} necunoscut in PID_MAP")

    data_bytes_hex = tokens[2:2 + pid_def.num_bytes]
    if len(data_bytes_hex) < pid_def.num_bytes:
        raise ParseError(f"Nu sunt suficienti octeti de date pentru PID {pid}: '{cleaned}'")

    try:
        data_bytes = [int(b, 16) for b in data_bytes_hex]
    except ValueError as exc:
        raise ParseError(f"Octeti de date invalizi pentru PID {pid}: '{cleaned}'") from exc

    return pid_def.formula(*data_bytes)


def _decode_single_dtc(byte1: int, byte2: int) -> str | None:
    if byte1 == 0 and byte2 == 0:
        return None
    category_bits = (byte1 >> 6) & 0x03
    letter = ["P", "C", "B", "U"][category_bits]
    digit1 = (byte1 >> 4) & 0x03
    digit2 = byte1 & 0x0F
    digit3 = (byte2 >> 4) & 0x0F
    digit4 = byte2 & 0x0F
    return f"{letter}{digit1}{digit2:X}{digit3:X}{digit4:X}"


def parse_dtc_response(raw_response: str) -> list[str]:
    cleaned = clean_response(raw_response).upper()
    if any(err in cleaned for err in ELM_ERROR_RESPONSES):
        return []

    tokens = cleaned.split()
    try:
        response_start = tokens.index("43")
    except ValueError:
        raise ParseError(f"Raspuns neasteptat la citire DTC: '{cleaned}'")

    data = tokens[response_start + 1:]
    codes = []
    for i in range(0, len(data) - 1, 2):
        try:
            b1, b2 = int(data[i], 16), int(data[i + 1], 16)
        except ValueError:
            continue
        code = _decode_single_dtc(b1, b2)
        if code:
            codes.append(code)
    return codes