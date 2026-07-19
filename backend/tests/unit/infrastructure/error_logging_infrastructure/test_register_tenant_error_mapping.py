from backend.app.infrastructure.logging.error_logger import ErrorLogger
from backend.app.infrastructure.logging.models import ErrorCode


def test_business_rule_exception_is_not_mapped_to_auth_failed():
    error_logger = ErrorLogger(session_factory=None)

    exception = RuntimeError("Tenant slug already exists")
    status_code, error_code = error_logger._map_exception_to_status_and_code(exception)

    assert status_code == 500
    assert error_code == ErrorCode.INTERNAL_ERROR
