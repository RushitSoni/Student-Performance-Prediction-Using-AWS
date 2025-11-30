import json
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

import handler  # Your lambda file (handler.py)


# ---------------------------
# TEST: CREATE
# ---------------------------
@patch("handler.runtime")
@patch("handler.table")
def test_create_student(mock_table, mock_runtime):
    mock_runtime.invoke_endpoint.return_value = {
        "Body": MagicMock(read=lambda: b'{"prediction": [85]}')
    }

    event = {
        "operation": "CREATE",
        "data": {"StudentID": "1", "Hours_Studied": 5.0}
    }

    response = handler.lambda_handler(event, None)

    mock_table.put_item.assert_called_once()
    assert response["success"] is True
    assert response["prediction"] == [85]


# ---------------------------
# TEST: READ (single)
# ---------------------------
@patch("handler.table")
def test_read_single(mock_table):
    mock_table.get_item.return_value = {
        "Item": {"StudentID": "1", "Hours_Studied": Decimal("5")}
    }

    event = {"operation": "READ", "data": {"StudentID": "1"}}

    response = handler.lambda_handler(event, None)

    assert response["success"] is True
    assert response["data"][0]["Hours_Studied"] == 5.0


# ---------------------------
# TEST: UPDATE
# ---------------------------
@patch("handler.runtime")
@patch("handler.table")
def test_update_student(mock_table, mock_runtime):
    mock_runtime.invoke_endpoint.return_value = {
        "Body": MagicMock(read=lambda: b'{"prediction": [90]}')
    }

    event = {
        "operation": "UPDATE",
        "data": {"StudentID": "1", "Hours_Studied": 6.0}
    }

    response = handler.lambda_handler(event, None)

    mock_table.update_item.assert_called_once()
    assert response["success"] is True
    assert response["prediction"] == [90]


# ---------------------------
# TEST: DELETE
# ---------------------------
@patch("handler.table")
def test_delete_student(mock_table):
    event = {
        "operation": "DELETE",
        "data": {"StudentID": "1"}
    }

    response = handler.lambda_handler(event, None)

    mock_table.delete_item.assert_called_once()
    assert response["success"] is True
