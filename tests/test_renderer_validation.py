import pytest

from card_renderer import validate_render_card


def _valid_card(**overrides):
    card = {
        "slide": 2,
        "type": "news",
        "headline": "New model announced",
        "body": ["Key point", "Supporting point"],
        "visual_type": "diagram",
    }
    card.update(overrides)
    return card


def test_validate_render_card_rejects_missing_headline():
    card = _valid_card()
    del card["headline"]

    with pytest.raises(ValueError, match="missing field.*headline"):
        validate_render_card(card)


def test_validate_render_card_rejects_invalid_visual_type():
    card = _valid_card(visual_type="photo")

    with pytest.raises(ValueError, match="visual_type"):
        validate_render_card(card)
