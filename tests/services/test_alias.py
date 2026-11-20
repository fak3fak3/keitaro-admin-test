import re

from app.services.alias import make_alias


def test_alias_is_slug_of_name_with_random_suffix():
    alias = make_alias("MX test 20-11")

    assert re.fullmatch(r"mx-test-20-11-[a-z0-9]{6}", alias)


def test_aliases_for_same_name_differ():
    assert make_alias("Same") != make_alias("Same")


def test_name_without_latin_letters_and_digits_falls_back_to_campaign():
    assert re.fullmatch(r"campaign-[a-z0-9]{6}", make_alias("Кампания !!!"))


def test_long_name_is_truncated():
    alias = make_alias("a" * 100)

    assert len(alias) <= 47
    assert not alias.startswith("-")
