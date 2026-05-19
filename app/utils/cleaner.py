"""Markdown cleanup utilities for scraped content."""

import re
from typing import Optional

_EMPTY_LINK_RE = re.compile(r"^\s*\[\]\([^)]+\)\s*$")
_EMPTY_IMAGE_RE = re.compile(r"^\s*!\[\]\([^)]+\)\s*$")
_REPEATED_SPACE_RE = re.compile(r"[ \t]{2,}")
_KBD_NOISE_RE = re.compile(r"^(?:`[^`]+`){2,}$")
_INLINE_EMPTY_LINK_RE = re.compile(r"\[\]\([^)]+\)")
_INLINE_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_IMAGE_ONLY_LINE_RE = re.compile(r"^\s*!\[[^\]]*\]\([^)]+\)\s*$")
_LINK_ONLY_LINE_RE = re.compile(r"^\s*(?:\[[^\]]+\]\([^)]+\)\s*)+$")
_LEADING_NOISE_LINK_RE = re.compile(r"^\s*\[\s*!+\s*\]\([^)]+\)\s*")

def clean_markdown(markdown: Optional[str]) -> Optional[str]:
    """
    Conservative markdown cleanup aimed at agent consumption.
    Keeps core content and removes obvious extraction artifacts.
    """
    if not markdown:
        return markdown

    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned: list[str] = []
    previous_nonempty: Optional[str] = None
    seen: dict[str, int] = {}
    blank_run = 0
    in_code_block = False
    in_content = False

    for raw_line in lines:
        line = _REPEATED_SPACE_RE.sub(" ", raw_line.rstrip())
        line = _INLINE_EMPTY_LINK_RE.sub("", line)
        line = _INLINE_IMAGE_RE.sub("", line)
        line = _LEADING_NOISE_LINK_RE.sub("", line)
        stripped = line.strip()

        # Keep code fences/content largely intact.
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            cleaned.append(stripped)
            previous_nonempty = stripped
            blank_run = 0
            continue
        if in_code_block:
            # Keep code blocks compact for downstream agents:
            # drop blank lines and trailing whitespace noise.
            code_line = raw_line.rstrip()
            if not code_line.strip():
                continue
            cleaned.append(code_line)
            continue

        # Drop obvious nav/markup artifacts.
        if (
            _EMPTY_LINK_RE.match(stripped)
            or _EMPTY_IMAGE_RE.match(stripped)
            or _IMAGE_ONLY_LINE_RE.match(stripped)
        ):
            continue
        if _KBD_NOISE_RE.match(stripped) and len(stripped) <= 24:
            continue

        if stripped.lower().startswith("copyright"):
            break
        if stripped.lower().startswith("logo by"):
            break

        # Drop "header nav" style lines until we hit real content.
        if not in_content:
            if stripped.startswith("#"):
                in_content = True
            elif _LINK_ONLY_LINE_RE.match(stripped) or not stripped:
                continue
            else:
                in_content = True

        # Keep at most one empty line in a row.
        if not stripped:
            blank_run += 1
            if blank_run > 1:
                continue
            cleaned.append("")
            continue

        blank_run = 0

        # Remove exact consecutive duplicate lines.
        if stripped == previous_nonempty:
            continue

        # Remove repeated short/noisy lines globally.
        count = seen.get(stripped, 0)
        if count > 0 and (
            len(stripped) <= 24
            or _LINK_ONLY_LINE_RE.match(stripped)
            or stripped.lower() in {"search", "more", "uwu?", "no uwu plz"}
        ):
            continue
        if stripped.lower() in {"search", "more", "uwu?", "no uwu plz", "copyright © meta platforms, inc"}:
            continue
        seen[stripped] = count + 1

        cleaned.append(line)
        previous_nonempty = stripped

    result = "\n".join(cleaned).strip()
    return result or None
