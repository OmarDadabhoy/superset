# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
# pylint: disable=unused-argument, import-outside-toplevel, protected-access

from datetime import datetime
from typing import Optional

import pytest
from pytest_mock import MockerFixture

from superset.db_engine_specs.databricks import DatabricksNativeEngineSpec
from superset.errors import ErrorLevel, SupersetError, SupersetErrorType
from superset.utils import json
from tests.unit_tests.db_engine_specs.utils import assert_convert_dttm
from tests.unit_tests.fixtures.common import dttm  # noqa: F401


def test_get_parameters_from_uri() -> None:
    """
    Test that the result from ``get_parameters_from_uri`` is JSON serializable.
    """
    from superset.db_engine_specs.databricks import (
        DatabricksNativeEngineSpec,
        DatabricksNativeParametersType,
    )

    parameters = DatabricksNativeEngineSpec.get_parameters_from_uri(
        "databricks+connector://token:abc12345@my_hostname:1234/test"
    )
    assert parameters == DatabricksNativeParametersType(
        {
            "access_token": "abc12345",
            "host": "my_hostname",
            "port": 1234,
            "database": "test",
            "encryption": False,
        }
    )
    assert json.loads(json.dumps(parameters)) == parameters


def test_build_sqlalchemy_uri() -> None:
    """
    test that the parameters are can correctly be compiled into a
    sqlalchemy_uri
    """
    from superset.db_engine_specs.databricks import (
        DatabricksNativeEngineSpec,
        DatabricksNativeParametersType,
    )

    parameters = DatabricksNativeParametersType(
        {
            "access_token": "abc12345",
            "host": "my_hostname",
            "port": 1234,
            "database": "test",
            "encryption": False,
        }
    )
    encrypted_extra = None
    sqlalchemy_uri = DatabricksNativeEngineSpec.build_sqlalchemy_uri(
        parameters, encrypted_extra
    )
    assert sqlalchemy_uri == (
        "databricks+connector://token:abc12345@my_hostname:1234/test"
    )


def test_parameters_json_schema() -> None:
    """
    test that the parameters schema can be converted to json
    """
    from superset.db_engine_specs.databricks import DatabricksNativeEngineSpec

    json_schema = DatabricksNativeEngineSpec.parameters_json_schema()

    assert json_schema == {
        "type": "object",
        "properties": {
            "access_token": {"type": "string"},
            "database": {"type": "string"},
            "encryption": {
                "description": "Use an encrypted connection to the database",
                "type": "boolean",
            },
            "host": {"type": "string"},
            "http_path": {"type": "string"},
            "port": {
                "description": "Database port",
                "maximum": 65536,
                "minimum": 0,
                "type": "integer",
            },
        },
        "required": ["access_token", "database", "host", "http_path", "port"],
    }


def test_get_extra_params(mocker: MockerFixture) -> None:
    """
    Test the ``get_extra_params`` method.
    """
    from superset.db_engine_specs.databricks import DatabricksNativeEngineSpec

    database = mocker.MagicMock()

    database.extra = {}
    assert DatabricksNativeEngineSpec.get_extra_params(database) == {
        "engine_params": {
            "connect_args": {
                "http_headers": [("User-Agent", "Apache Superset")],
                "_user_agent_entry": "Apache Superset",
            }
        }
    }

    database.extra = json.dumps(
        {
            "engine_params": {
                "connect_args": {
                    "http_headers": [("User-Agent", "Custom user agent")],
                    "_user_agent_entry": "Custom user agent",
                    "foo": "bar",
                }
            }
        }
    )
    assert DatabricksNativeEngineSpec.get_extra_params(database) == {
        "engine_params": {
            "connect_args": {
                "http_headers": [["User-Agent", "Custom user agent"]],
                "_user_agent_entry": "Custom user agent",
                "foo": "bar",
            }
        }
    }

    # it should also remove whitespace from http_path
    database.extra = json.dumps(
        {
            "engine_params": {
                "connect_args": {
                    "http_headers": [("User-Agent", "Custom user agent")],
                    "_user_agent_entry": "Custom user agent",
                    "http_path": "/some_path_here_with_whitespace ",
                }
            }
        }
    )
    assert DatabricksNativeEngineSpec.get_extra_params(database) == {
        "engine_params": {
            "connect_args": {
                "http_headers": [["User-Agent", "Custom user agent"]],
                "_user_agent_entry": "Custom user agent",
                "http_path": "/some_path_here_with_whitespace",
            }
        }
    }


def test_extract_errors() -> None:
    """
    Test that custom error messages are extracted correctly.
    """

    msg = ": mismatched input 'from_'. Expecting: "
    result = DatabricksNativeEngineSpec.extract_errors(Exception(msg))

    assert result == [
        SupersetError(
            message=": mismatched input 'from_'. Expecting: ",
            error_type=SupersetErrorType.GENERIC_DB_ENGINE_ERROR,
            level=ErrorLevel.ERROR,
            extra={
                "engine_name": "Databricks (legacy)",
                "issue_codes": [
                    {
                        "code": 1002,
                        "message": "Issue 1002 - The database returned an unexpected error.",  # noqa: E501
                    }
                ],
            },
        )
    ]


def test_extract_errors_with_context() -> None:
    """
    Test that custom error messages are extracted correctly with context.
    """

    msg = ": mismatched input 'from_'. Expecting: "
    context = {"hostname": "foo"}
    result = DatabricksNativeEngineSpec.extract_errors(Exception(msg), context)

    assert result == [
        SupersetError(
            message=": mismatched input 'from_'. Expecting: ",
            error_type=SupersetErrorType.GENERIC_DB_ENGINE_ERROR,
            level=ErrorLevel.ERROR,
            extra={
                "engine_name": "Databricks (legacy)",
                "issue_codes": [
                    {
                        "code": 1002,
                        "message": "Issue 1002 - The database returned an unexpected error.",  # noqa: E501
                    }
                ],
            },
        )
    ]


@pytest.mark.parametrize(
    "target_type,expected_result",
    [
        ("Date", "CAST('2019-01-02' AS DATE)"),
        (
            "TimeStamp",
            "CAST('2019-01-02 03:04:05.678900' AS TIMESTAMP)",
        ),
        ("UnknownType", None),
    ],
)
def test_convert_dttm(
    target_type: str,
    expected_result: Optional[str],
    dttm: datetime,  # noqa: F811
) -> None:
    from superset.db_engine_specs.databricks import (
        DatabricksNativeEngineSpec as spec,  # noqa: N813
    )

    assert_convert_dttm(spec, target_type, expected_result, dttm)


def test_get_prequeries(mocker: MockerFixture) -> None:
    """
    Test the ``get_prequeries`` method.
    """
    from superset.db_engine_specs.databricks import DatabricksNativeEngineSpec

    database = mocker.MagicMock()

    assert DatabricksNativeEngineSpec.get_prequeries(database) == []
    assert DatabricksNativeEngineSpec.get_prequeries(database, schema="test") == [
        "USE SCHEMA `test`",
    ]
    assert DatabricksNativeEngineSpec.get_prequeries(database, catalog="test") == [
        "USE CATALOG `test`",
    ]
    assert DatabricksNativeEngineSpec.get_prequeries(
        database, catalog="foo", schema="bar"
    ) == [
        "USE CATALOG `foo`",
        "USE SCHEMA `bar`",
    ]

    assert DatabricksNativeEngineSpec.get_prequeries(
        database, catalog="with-hyphen", schema="hyphen-again"
    ) == [
        "USE CATALOG `with-hyphen`",
        "USE SCHEMA `hyphen-again`",
    ]

    assert DatabricksNativeEngineSpec.get_prequeries(
        database, catalog="`escaped-hyphen`", schema="`hyphen-escaped`"
    ) == [
        "USE CATALOG ```escaped-hyphen```",
        "USE SCHEMA ```hyphen-escaped```",
    ]

    assert DatabricksNativeEngineSpec.get_prequeries(
        database, catalog="evil` USE CATALOG bad", schema="evil` USE SCHEMA bad"
    ) == [
        "USE CATALOG `evil`` USE CATALOG bad`",
        "USE SCHEMA `evil`` USE SCHEMA bad`",
    ]


def test_quote_databricks_identifier() -> None:
    """
    Test that ``_quote_databricks_identifier`` backtick-quotes identifiers.
    """
    from superset.db_engine_specs.databricks import _quote_databricks_identifier

    assert _quote_databricks_identifier("simple") == "`simple`"
    assert _quote_databricks_identifier("my-staging-catalog") == "`my-staging-catalog`"
    assert _quote_databricks_identifier("my-poc-schema") == "`my-poc-schema`"
    assert _quote_databricks_identifier("has`backtick") == "`has``backtick`"
    assert _quote_databricks_identifier("evil` DROP TABLE x") == "`evil`` DROP TABLE x`"


def test_monkeypatch_databricks_dialect_get_table_names(mocker: MockerFixture) -> None:
    """
    Test that the monkeypatched ``get_table_names`` quotes hyphenated identifiers.
    """
    from databricks.sqlalchemy.dialect import DatabricksDialect

    dialect = DatabricksDialect.__new__(DatabricksDialect)
    dialect.catalog = "my-staging-catalog"
    dialect.schema = "my-poc-schema"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute.return_value.fetchall.return_value = [
        ("", "orders", False),
        ("", "customers", False),
    ]
    mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = mocker.MagicMock(return_value=False)

    mocker.patch.object(dialect, "get_connection_cursor", return_value=mock_cursor)

    connection = mocker.MagicMock()
    result = dialect.get_table_names(connection)

    mock_cursor.execute.assert_called_once_with(
        "SHOW TABLES FROM `my-staging-catalog`.`my-poc-schema`"
    )
    assert result == ["orders", "customers"]


def test_monkeypatch_databricks_dialect_get_view_names(mocker: MockerFixture) -> None:
    """
    Test that the monkeypatched ``get_view_names`` quotes hyphenated identifiers.
    """
    from databricks.sqlalchemy.dialect import DatabricksDialect

    dialect = DatabricksDialect.__new__(DatabricksDialect)
    dialect.catalog = "my-staging-catalog"
    dialect.schema = "my-poc-schema"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute.return_value.fetchall.return_value = [
        ("", "v_orders", False),
    ]
    mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = mocker.MagicMock(return_value=False)

    mocker.patch.object(dialect, "get_connection_cursor", return_value=mock_cursor)

    connection = mocker.MagicMock()
    result = dialect.get_view_names(connection)

    mock_cursor.execute.assert_called_once_with(
        "SHOW VIEWS FROM `my-staging-catalog`.`my-poc-schema`"
    )
    assert result == ["v_orders"]


def test_monkeypatch_databricks_dialect_has_table(mocker: MockerFixture) -> None:
    """
    Test that the monkeypatched ``has_table`` quotes hyphenated identifiers.
    """
    from databricks.sqlalchemy.dialect import DatabricksDialect

    dialect = DatabricksDialect.__new__(DatabricksDialect)
    dialect.catalog = "my-staging-catalog"
    dialect.schema = "my-poc-schema"

    connection = mocker.MagicMock()

    result = dialect.has_table(connection, "my-table")

    connection.execute.assert_called_once_with(
        "DESCRIBE TABLE `my-staging-catalog`.`my-poc-schema`.`my-table`"
    )
    assert result is True


def test_monkeypatch_databricks_dialect_has_table_not_found(
    mocker: MockerFixture,
) -> None:
    """
    Test that the monkeypatched ``has_table`` returns False for missing tables.
    """
    from databricks.sqlalchemy.dialect import DatabricksDialect
    from sqlalchemy.exc import DatabaseError

    dialect = DatabricksDialect.__new__(DatabricksDialect)
    dialect.catalog = "my-staging-catalog"
    dialect.schema = "my-poc-schema"

    connection = mocker.MagicMock()
    connection.execute.side_effect = DatabaseError("TABLE_OR_VIEW_NOT_FOUND", {}, None)

    result = dialect.has_table(connection, "nonexistent")
    assert result is False


def test_monkeypatch_databricks_dialect_schema_override(
    mocker: MockerFixture,
) -> None:
    """
    Test that the monkeypatched methods respect an explicit schema argument.
    """
    from databricks.sqlalchemy.dialect import DatabricksDialect

    dialect = DatabricksDialect.__new__(DatabricksDialect)
    dialect.catalog = "prod-catalog"
    dialect.schema = "default"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute.return_value.fetchall.return_value = [
        ("", "events", False),
    ]
    mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = mocker.MagicMock(return_value=False)

    mocker.patch.object(dialect, "get_connection_cursor", return_value=mock_cursor)

    connection = mocker.MagicMock()
    result = dialect.get_table_names(connection, schema="analytics-schema")

    mock_cursor.execute.assert_called_once_with(
        "SHOW TABLES FROM `prod-catalog`.`analytics-schema`"
    )
    assert result == ["events"]
