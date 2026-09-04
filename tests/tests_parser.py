import pytest
from protocol.parser import parse_pid_response, parse_dtc_response, parse_vin_response, ParseError
from protocol.vin import decode_vin


def test_pid_rpm():
    assert parse_pid_response("0C", "41 0C 1A F8\r\r>") == 1726.0

def test_pid_rpm_cu_searching():
    assert parse_pid_response("0C", "SEARCHING...\r41 0C 1A F8\r>") == 1726.0

def test_pid_no_data():
    with pytest.raises(ParseError):
        parse_pid_response("0C", "NO DATA\r>")

def test_pid_ecou_gresit():
    with pytest.raises(ParseError):
        parse_pid_response("0D", "41 0C 1A F8\r>")

def test_dtc_un_cod():
    assert parse_dtc_response("43 01 33 00 00\r>") == ["P0133"]

def test_dtc_un_cod_cu_header_can():
    assert parse_dtc_response("7E8 05 43 01 33 00 00\r>") == ["P0133"]

def test_dtc_sloturi_goale():
    assert parse_dtc_response("43 00 00 00 00\r>") == []

def test_dtc_no_data():
    assert parse_dtc_response("NO DATA\r>") == []

def test_vin_multi_linie():
    raw = (
        "49 02 01 57 50 30 5A 5A 5A 39 39\r"
        "49 02 02 5A 54 53 33 39 30 30 30\r"
        "49 02 03 30 30 30 00 00 00 00 00\r>"
    )
    assert parse_vin_response(raw) == "WP0ZZZ99ZTS390000"

def test_vin_indisponibil():
    with pytest.raises(ParseError):
        parse_vin_response("NO DATA\r>")

def test_vin_cadre_numerotate_de_emulator():
    raw = (
        "014\r0: 49 02 01 4D 41 54 \r"
        "1: 34 30 33 30 39 36 42 \r"
        "2: 4E 4C 30 30 30 30 30 \r\r>"
    )
    assert parse_vin_response(raw) == "MAT403096BNL00000"

def test_decode_vin():
    details = decode_vin("WP0ZZZ99ZTS390000")
    assert details["producator"] == "Porsche"
    assert details["tara"] == "Germania"
    assert details["an_model"] == "1996/2026"
    assert details["fabrica"] == "S"
    assert details["serie"] == "390000"