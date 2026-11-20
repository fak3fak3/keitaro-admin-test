import re
import secrets
import string

MAX_SLUG_LENGTH = 40
SUFFIX_ALPHABET = string.ascii_lowercase + string.digits
SUFFIX_LENGTH = 6


def make_alias(name: str) -> str:
    """Alias кампании для URL: slug имени + случайный суффикс, чтобы не пересекаться с чужими."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug = slug[:MAX_SLUG_LENGTH].strip("-") or "campaign"
    suffix = "".join(secrets.choice(SUFFIX_ALPHABET) for _ in range(SUFFIX_LENGTH))
    return f"{slug}-{suffix}"
