from app import _ship_type_description


def test_ship_type_description_known():
    assert _ship_type_description(30) == "Fiskefartøy"


def test_ship_type_description_unknown():
    assert _ship_type_description(999) == "Unknown"
