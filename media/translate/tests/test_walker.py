from translate.walker import DEFAULT_FIELDS, is_already_translated, iter_strings


def test_walks_default_fields_in_nested_doc():
    doc = {
        "title": "T1",
        "days": [
            {"heading": "H1", "items": [{"title": "X", "summary": "S", "url": "http://"}]},
            {"heading": "", "items": []},
        ],
    }
    found = [(k, v) for _, k, v in iter_strings(doc)]
    assert ("title", "T1") in found
    assert ("heading", "H1") in found
    assert ("title", "X") in found
    assert ("summary", "S") in found
    assert all(k != "url" for k, _ in found)
    assert all(v != "" for _, v in found)


def test_field_override():
    doc = {"title": "T", "summary": "S"}
    found = [(k, v) for _, k, v in iter_strings(doc, fields={"summary"})]
    assert found == [("summary", "S")]


def test_is_already_translated_detects_sibling():
    container = {"title": "T", "title_en": "T(en)"}
    assert is_already_translated(container, "title", "en") is True
    assert is_already_translated(container, "title", "ja") is False
