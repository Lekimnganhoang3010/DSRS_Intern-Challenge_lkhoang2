"""Write parsed 13F records using the required Parquet schemas."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


FILINGS_SCHEMA = pa.schema(
    [
        pa.field("accession_number", pa.string(), nullable=False),
        pa.field("cik", pa.string(), nullable=False),
        pa.field("fund_name", pa.string(), nullable=False),
        pa.field("filing_manager", pa.string(), nullable=False),
        pa.field("form_type", pa.string(), nullable=False),
        pa.field("report_period", pa.date32(), nullable=False),
        pa.field("report_quarter", pa.string(), nullable=False),
        pa.field("filing_date", pa.date32(), nullable=False),
        pa.field("is_amendment", pa.bool_(), nullable=False),
        pa.field("amendment_no", pa.int32(), nullable=True),
        pa.field("amendment_type", pa.string(), nullable=True),
        pa.field("report_type", pa.string(), nullable=False),
        pa.field("form_13f_file_number", pa.string(), nullable=True),
        pa.field("crd_number", pa.string(), nullable=True),
        pa.field("sec_file_number", pa.string(), nullable=True),
        pa.field(
            "other_included_managers_count",
            pa.int32(),
            nullable=True,
        ),
        pa.field("table_entry_total", pa.int64(), nullable=True),
        pa.field("table_value_total", pa.int64(), nullable=True),
    ]
)


HOLDINGS_SCHEMA = pa.schema(
    [
        pa.field("accession_number", pa.string(), nullable=False),
        pa.field("cik", pa.string(), nullable=False),
        pa.field("report_quarter", pa.string(), nullable=False),
        pa.field("name_of_issuer", pa.string(), nullable=False),
        pa.field("title_of_class", pa.string(), nullable=False),
        pa.field("cusip", pa.string(), nullable=False),
        pa.field("figi", pa.string(), nullable=True),
        pa.field("value", pa.int64(), nullable=False),
        pa.field("ssh_prnamt", pa.int64(), nullable=False),
        pa.field("ssh_prnamt_type", pa.string(), nullable=False),
        pa.field("put_call", pa.string(), nullable=True),
        pa.field(
            "investment_discretion",
            pa.string(),
            nullable=False,
        ),
        pa.field("other_manager", pa.string(), nullable=True),
        pa.field("voting_sole", pa.int64(), nullable=False),
        pa.field("voting_shared", pa.int64(), nullable=False),
        pa.field("voting_none", pa.int64(), nullable=False),
    ]
)


def write_table(
    rows: list[dict[str, object]],
    schema: pa.Schema,
    destination: Path,
) -> None:
    """Write one table atomically with deterministic settings."""
    table = pa.Table.from_pylist(rows, schema=schema)

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_suffix(".parquet.tmp")

    pq.write_table(
        table,
        temporary_path,
        compression="snappy",
        use_dictionary=True,
        write_statistics=True,
    )

    temporary_path.replace(destination)


def write_parquet_outputs(
    filing_rows: list[dict[str, object]],
    holding_rows: list[dict[str, object]],
    output_dir: Path,
) -> None:
    """Write both required Parquet outputs."""
    write_table(
        filing_rows,
        FILINGS_SCHEMA,
        output_dir / "filings.parquet",
    )
    write_table(
        holding_rows,
        HOLDINGS_SCHEMA,
        output_dir / "holdings.parquet",
    )
