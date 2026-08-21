from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from lxml import etree


def local_name(element: etree._Element) -> str:
    """Return an XML element's name without its namespace."""
    return etree.QName(element).localname


def find_elements(
    root: etree._Element,
    name: str,
) -> list[etree._Element]:
    """Find every descendant having the requested local name."""
    return root.xpath(f'.//*[local-name()="{name}"]')


def find_first(
    root: etree._Element,
    name: str,
) -> etree._Element | None:
    """Find the first descendant having the requested local name."""
    matches = find_elements(root, name)
    return matches[0] if matches else None


def find_text(
    root: etree._Element,
    name: str,
    required: bool = False,
) -> str | None:
    """Extract and clean text from the first matching element."""
    element = find_first(root, name)

    if element is None or element.text is None:
        if required:
            raise ValueError(f"Required XML element is missing: {name}")
        return None

    value = element.text.strip()

    if not value:
        if required:
            raise ValueError(f"Required XML element is empty: {name}")
        return None

    return value