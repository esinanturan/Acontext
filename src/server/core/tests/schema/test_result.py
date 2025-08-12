import pytest
from pydantic import ValidationError
from acontext_server.schema.pydantic.result import Result, Code
from acontext_server.schema.pydantic.api.response import BasicResponse
from fastapi.responses import JSONResponse


def test_result_class():
    test_data = {"message": "pong"}
    suc = Result.resolve(test_data)
    d, eil = suc.unpack()
    assert d == test_data
    assert eil is None

    err = Result.reject(Code.BAD_REQUEST, "test")
    d, eil = err.unpack()
    assert d is None
    assert eil.status == Code.BAD_REQUEST

    suc = Result.resolve(test_data)
    p = suc.to_response(BasicResponse[dict[str, str]])
    assert p.status_code == 200

    with pytest.raises(ValidationError):
        Result.resolve(test_data).to_response(BasicResponse[int])
