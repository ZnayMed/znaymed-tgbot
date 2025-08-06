from .ru import LEXICON_RU


def t(key: str) -> str:
    return LEXICON_RU.get(key, key)
