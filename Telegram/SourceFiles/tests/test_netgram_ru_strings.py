#!/usr/bin/env python3
"""Built-in Russian translation (Resources/langs/netgram_ru.strings).

It is applied by ayu/ayu_lang.cpp over the current language pack when the
interface language is Russian, so every key must be a real lang.strings key
with the same placeholders, and plural keys need all Russian forms.
"""

import re
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]
LANGS = SOURCE_DIR.parent / "Resources" / "langs"
LANG = LANGS / "lang.strings"
RU = LANGS / "netgram_ru.strings"
AYU_LANG_CPP = SOURCE_DIR / "ayu" / "ayu_lang.cpp"
TELEGRAM_QRC = SOURCE_DIR.parent / "Resources" / "qrc" / "telegram" / "telegram.qrc"

LINE = re.compile(r'^"([A-Za-z0-9_#]+)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;\s*$')
TAG = re.compile(r"\{([A-Za-z0-9_]+)\}")
RU_FORMS = ("one", "few", "many", "other")


def parse(path):
    result = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith('"'):
            match = LINE.match(line)
            assert match, f"{path.name}:{number} is not a valid lang line"
            assert match.group(1) not in result, f"{path.name}: duplicate {match.group(1)}"
            result[match.group(1)] = match.group(2)
    return result


def english_for(lang, key):
    if key in lang:
        return lang[key]
    return lang.get(key.split("#")[0] + "#other")


def test_ru_keys_exist_and_keep_placeholders():
    lang = parse(LANG)
    ru = parse(RU)
    plural_bases = {key.split("#")[0] for key in lang if "#" in key}
    for key, value in ru.items():
        base, _, form = key.partition("#")
        if form:
            assert base in plural_bases, f"{key}: not a plural key in lang.strings"
            assert form in RU_FORMS, f"{key}: unexpected plural form"
        else:
            assert key in lang, f"{key}: missing in lang.strings"
        english = english_for(lang, key)
        assert set(TAG.findall(value)) == set(TAG.findall(english)), (
            f"{key}: placeholders differ from English")
        assert value.count("**") == english.count("**"), f"{key}: ** markup differs"


def test_ru_plural_keys_have_all_forms():
    ru = parse(RU)
    bases = {key.split("#")[0] for key in ru if "#" in key}
    for base in bases:
        for form in RU_FORMS:
            assert f"{base}#{form}" in ru, f"{base}: missing #{form}"


def test_every_ayu_key_is_translated():
    lang = parse(LANG)
    ru = parse(RU)
    for key in lang:
        if not key.startswith("ayu_"):
            continue
        base, _, form = key.partition("#")
        target = f"{base}#other" if form else key
        assert target in ru, f"{key}: no Russian translation"


def test_translation_is_embedded_and_not_downloaded():
    qrc = TELEGRAM_QRC.read_text(encoding="utf-8")
    source = AYU_LANG_CPP.read_text(encoding="utf-8")
    assert '<file alias="langs/netgram_ru.strings">../../langs/netgram_ru.strings</file>' in qrc
    assert ":/misc/langs/netgram_ru.strings" in source
    for forbidden in ("jsdelivr", "AyuGram/Languages", "QNetworkAccessManager", "ayu/languages"):
        assert forbidden not in source, forbidden


if __name__ == "__main__":
    test_ru_keys_exist_and_keep_placeholders()
    test_ru_plural_keys_have_all_forms()
    test_every_ayu_key_is_translated()
    test_translation_is_embedded_and_not_downloaded()
