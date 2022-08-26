"""
Provides means to reason about data serialization to and from various formats
"""

import csv
from enum import Enum, auto
from typing import IO, Any, ClassVar, Dict, Mapping, Optional, Set, Type

from aiohttp import FormData, JsonPayload, Payload
from marshmallow import EXCLUDE, INCLUDE, Schema, post_dump


class OutputFormat(Enum):
    """
    Denotes the type of serialization format
    """

    RAW = auto()
    """Used to signify serialization to raw byte content"""

    CSV = auto()
    """Used to signify serialization to Comma-separated-values data"""

    JSON = auto()
    """Used to signify serialization to JSON"""

    FORM = auto()
    """Used to signify serialization to x-www-formurlencoded format"""


class CsvDialect(Enum):
    """
    Specifies the type of CSV dialect used in serialization. Uses the same names as the python standard library module
    csv.
    """

    UNIX = auto()
    EXCEL = auto()
    EXCEL_TAB = auto()

    def to_str(self) -> str:
        """
        Converts the enum Variant to a string as understood by the standard library module csv
        """
        if self is CsvDialect.UNIX:
            return "unix"
        elif self is CsvDialect.EXCEL:
            return "excel"
        elif self is CsvDialect.EXCEL_TAB:
            return "excel-tab"
        else:
            raise NotImplementedError(f"Unsupported CSV dialect: {self}")


def field_names(schema: Schema) -> Set[str]:
    """
    Returns the names of fields of serializable data taking into account if they were renamed in the schema

    :param schema: A valid Marshmallow schema
    :return: An unordered set of field names
    """
    return {
        v.data_key if v.data_key is not None else k for k, v in schema.fields.items()
    }


def dump_csv(
    schema: Schema,
    obj: Any,
    fp: IO[str],
    *,
    many: bool = False,
    dialect: CsvDialect = CsvDialect.EXCEL,
) -> None:
    """
    Serializes the specified python object to CSV based on the Marshmallow schema.

    :param schema: A valid Marshmallow schema
    :param obj: A python object that is serializable by the specified schema
    :param fp: A file-like object that can be written to
    :param many: Optionally serialize a sequence of objects as specified in the schema (i.e. interpret obj as a sequence)
    :param dialect: Specify the CSV dialect to use as understood by the standard library module csv
    """
    csv_writer = csv.DictWriter(
        fp,
        fieldnames=list(field_names(schema)),
        dialect=dialect.to_str(),
    )

    csv_writer.writeheader()

    if many:
        csv_writer.writerows(schema.dump(obj, many=True))
    else:
        csv_writer.writerow(schema.dump(obj))


def dump_form_data(
    schema: Schema, obj: Any, *, many: Optional[bool] = None
) -> FormData:
    """
    Serialize a python object to HTTP form-encoded data

    :param schema: A valid Marshmallow schema
    :param obj: A python object that is serializable by the specified schema
    :param many: Optionally serialize a sequence of objects as specified in the schema (i.e. interpret obj as a sequence)
    :return: An object that represents encoded form data
    """
    native = schema.dump(obj, many=many)
    if isinstance(native, dict):
        return FormData(native)
    else:
        fd = FormData()
        for entry in native:
            for k, v in entry.items():
                fd.add_field(k, v)

        return fd


def dump_to_payload(
    data: "SerializableData",
    *,
    fmt: OutputFormat = OutputFormat.JSON,
    many: Optional[bool] = None,
) -> Payload:
    """
    Serialize an instance of :class:`~SerializableData` to JSON or form-encoded data for use in an HTTP body

    :param data: A python object
    :param fmt: The output format of the HTTP body payload
    :param many: Optionally serialize a sequence of objects as specified in the schema (i.e. interpret data as a sequence)
    :return: The HTTP payload object
    """
    if fmt == OutputFormat.JSON:
        native_data = data.Schema().dump(data, many=many)
        return JsonPayload(native_data)
    elif fmt == OutputFormat.FORM:
        form_data = dump_form_data(data.Schema(), data)
        return form_data()
    else:
        raise NotImplementedError(f"Unsupported output format {fmt}")


class SerializableData:
    """
    Indicates that an object is inherently serializable. It also provides the corresponding Marshmallow serialization schema.
    """

    Schema: ClassVar[Type[Schema]] = Schema


def rename_field(field_name: str) -> Dict[str, str]:
    """
    A shortcut to enable renaming a field during serialization.

    >>> from marshmallow_dataclass import dataclass
    >>> from dataclasses import field
    >>>
    >>> # Used so
    >>> @dataclass()
    >>> class A:
    >>>     alpha: int = field(metadata=rename_field('Alpha'))
    >>>
    >>> # Instead of so
    >>> @dataclass()\
    >>> class B:
    >>>     beta: int = field(metadata={'data_key': 'Beta'})
    """
    return {"data_key": field_name}


class PermissiveSchema(Schema):
    """
    The permissive base schema accepts superfluous data when deserializing, but does _not_ deserialize such data.
    """

    class Meta:
        """Contains meta-data for the Marshmallow base schema"""

        unknown = EXCLUDE


class DangerousSchema(Schema):
    """
    The dangerous base schema accepts superfluous data when deserializing,
    and integrates such data into the deserialized object without type validation.
    """

    class Meta:
        """Contains meta-data for the Marshmallow base schema"""

        unknown = INCLUDE


class SkipNoneSchema(PermissiveSchema):
    """
    This base schema removes None valued properties from the serialization, effectively
    only transmissing properties with assigned value.
    """

    skip_values = {None}

    @post_dump
    def remove_skip_values(
        self, data: Mapping[str, Any], **_kwargs: Any
    ) -> Dict[str, Any]:
        """
        As a post-dump action, remove any fields that have assigned None as their value from the serialization
        """
        return {k: v for k, v in data.items() if v not in self.skip_values}
