import tempfile
from dataclasses import field
from enum import Enum
from typing import Any, Type

import marshmallow
import pytest
from aiohttp import BytesPayload, JsonPayload, Payload
from marshmallow import Schema
from marshmallow_dataclass import dataclass

from reidun.serialization import (
    CsvDialect,
    DangerousSchema,
    OutputFormat,
    PermissiveSchema,
    SerializableData,
    SkipNoneSchema,
    dump_csv,
    dump_form_data,
    dump_to_payload,
    field_names,
    rename_field,
)


@dataclass
class Td(SerializableData):
    a: int = field(metadata={"data_key": "A"})
    b: bool


def test_output_format_is_enum_with_these_variants() -> None:
    assert issubclass(OutputFormat, Enum)
    assert OutputFormat.RAW in OutputFormat
    assert OutputFormat.JSON in OutputFormat
    assert OutputFormat.CSV in OutputFormat
    assert OutputFormat.FORM in OutputFormat


def test_csv_dialect_is_enum_with_these_variants() -> None:
    assert issubclass(CsvDialect, Enum)
    assert CsvDialect.UNIX in CsvDialect
    assert CsvDialect.EXCEL in CsvDialect
    assert CsvDialect.EXCEL_TAB in CsvDialect


def test_field_names_honours_renamed_fields() -> None:
    assert field_names(Td.Schema()) == {"A", "b"}


def test_dump_csv_serializes_correctly_for_single_data() -> None:
    td = Td(101, True)
    with tempfile.TemporaryFile("r+t") as f:
        dump_csv(td.Schema(), td, f, many=False, dialect=CsvDialect.UNIX)
        f.seek(0)
        assert f.read() in ('"A","b"\n"101","True"\n', '"b","A"\n"True","101"\n')


def test_dump_form_data_serializes_correctly() -> None:
    td = Td(101, True)
    data = dump_form_data(td.Schema(), td)
    payload = data()
    assert isinstance(payload, Payload)

    tdl = [Td(102, False), Td(4, True)]
    data = dump_form_data(td.Schema(), tdl, many=True)
    payload = data()
    assert isinstance(payload, Payload)


@pytest.mark.parametrize(
    "data,fmt,expected",
    [
        (Td(101, True), OutputFormat.JSON, JsonPayload),
        (Td(101, True), OutputFormat.FORM, BytesPayload),
    ],
)
def test_dump_to_payload_serializes_correctly(
    data: Any, fmt: OutputFormat, expected: Type[Payload]
) -> None:
    payload: Payload = dump_to_payload(data, fmt=fmt)
    assert isinstance(payload, expected)


def test_serializable_data_has_schema_attribute() -> None:
    assert issubclass(SerializableData.Schema, Schema)


def test_rename_returns_metadata_dict_with_data_key() -> None:
    assert rename_field("fieldname") == {"data_key": "fieldname"}


def test_permissive_schema_excludes_unknown_fields() -> None:
    assert PermissiveSchema.Meta.unknown == marshmallow.EXCLUDE


def test_dangerous_schema_includes_unknown_fields() -> None:
    assert DangerousSchema.Meta.unknown == marshmallow.INCLUDE


def test_skip_none_schema_is_permissive() -> None:
    assert issubclass(SkipNoneSchema, PermissiveSchema)


def test_skip_none_schema_removes_none_values_in_serialization() -> None:
    assert SkipNoneSchema.skip_values == {None}
    assert callable(SkipNoneSchema.remove_skip_values)
