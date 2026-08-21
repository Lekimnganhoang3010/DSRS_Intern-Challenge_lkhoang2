"""Locate and download XML documents from EDGAR filing archives."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from sec_client import SecClient


def identify_xml_kind(xml_bytes: bytes) -> str:
    """Identify a 13F XML document from its root element."""
    root = etree.fromstring(xml_bytes)
    root_name = etree.QName(root).localname.lower()

    if root_name == "edgarsubmission":
        return "primary"

    if root_name in {"informationtable", "infotable"}:
        return "information_table"

    return "unknown"


def download_filing_xmls(
    client: SecClient,
    filings: list[dict[str, str]],
    output_dir: Path,
) -> list[dict[str, str]]:
    """Download and identify XML documents for every filing."""
    enriched_filings: list[dict[str, str]] = []

    for filing in filings:
        cik = filing["cik"]
        accession = filing["accession_number"]
        accession_directory = accession.replace("-", "")

        archive_url = (
            "https://www.sec.gov/Archives/edgar/data/"
            f"{cik}/{accession_directory}"
        )
        cache_prefix = (
            f"sec/archives/{cik}/{accession_directory}"
        )

        index_data = client.get_json(
            f"{archive_url}/index.json",
            f"{cache_prefix}/index.json",
        )

        xml_names = sorted(
            {
                item["name"]
                for item in index_data["directory"]["item"]
                if item.get("name", "").lower().endswith(".xml")
            }
        )

        documents: dict[str, list[tuple[str, str, bytes]]] = {
            "primary": [],
            "information_table": [],
            "unknown": [],
        }

        for xml_name in xml_names:
            cache_key = f"{cache_prefix}/{xml_name}"
            xml_bytes = client.get_bytes(
                f"{archive_url}/{xml_name}",
                cache_key,
            )
            document_kind = identify_xml_kind(xml_bytes)

            documents[document_kind].append(
                (xml_name, cache_key, xml_bytes)
            )

        if len(documents["primary"]) != 1:
            raise ValueError(
                f"{accession}: expected one primary XML; "
                f"found {[item[0] for item in documents['primary']]}. "
                f"Unknown XML: "
                f"{[item[0] for item in documents['unknown']]}."
            )

        primary_name, primary_key, primary_bytes = (
            documents["primary"][0]
        )

        information_name = ""
        information_key = ""
        selected_bytes = primary_bytes

        if filing["form_type"].startswith("13F-HR"):
            if len(documents["information_table"]) != 1:
                raise ValueError(
                    f"{accession}: expected one information-table XML; "
                    f"found "
                    f"{[item[0] for item in documents['information_table']]}. "
                    f"Unknown XML: "
                    f"{[item[0] for item in documents['unknown']]}."
                )

            (
                information_name,
                information_key,
                selected_bytes,
            ) = documents["information_table"][0]

        filing_output = (
            output_dir
            / cik
            / f"{accession_directory}.xml"
        )
        filing_output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_output = filing_output.with_suffix(".xml.tmp")
        temporary_output.write_bytes(selected_bytes)
        temporary_output.replace(filing_output)

        enriched = dict(filing)
        enriched["primary_xml_path"] = str(
            client.cache_dir / primary_key
        )
        enriched["information_table_xml_path"] = (
            str(client.cache_dir / information_key)
            if information_key
            else ""
        )
        enriched["output_xml_path"] = str(filing_output)
        enriched["primary_xml_name"] = primary_name
        enriched["information_table_xml_name"] = information_name
        enriched_filings.append(enriched)

    return enriched_filings