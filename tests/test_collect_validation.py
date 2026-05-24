import collect


def test_is_usable_item_rejects_empty_title():
    item = {
        "title": "",
        "text": "Useful body text",
        "url": "https://example.com/story",
    }

    assert not collect.is_usable_item(item)


def test_is_usable_item_accepts_empty_body_text_when_title_and_url_exist():
    item = {
        "title": "Story title",
        "text": "",
        "url": "https://example.com/story",
    }

    assert collect.is_usable_item(item)
