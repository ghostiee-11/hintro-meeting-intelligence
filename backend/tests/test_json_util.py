import pytest

from app.services.llm.json_util import extract_json, normalize_analysis


def test_extract_json_from_fenced_block():
    assert extract_json('Here:\n```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_raw_json():
    assert extract_json('{"x": "y"}') == {"x": "y"}


def test_extract_json_raises_without_object():
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_normalizes_bare_number_citations():
    result = normalize_analysis({"summary": [{"text": "point", "citations": [0, 1]}]})
    assert [c.segment_index for c in result.summary[0].citations] == [0, 1]


def test_drops_empty_text_and_supports_snake_case():
    result = normalize_analysis(
        {
            "summary": [{"text": "", "citations": []}, {"text": "keep", "citations": [{"segmentIndex": 2}]}],
            "action_items": [{"task": "do it", "citations": [{"segmentIndex": 1}]}],
            "follow_ups": [{"text": "later", "citations": [0]}],
        }
    )
    assert len(result.summary) == 1
    assert result.summary[0].text == "keep"
    assert len(result.action_items) == 1
    assert len(result.follow_ups) == 1


def test_empty_input_yields_empty_lists():
    result = normalize_analysis({})
    assert result.summary == []
    assert result.action_items == []
