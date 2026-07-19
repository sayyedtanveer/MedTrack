from backend.app.application.setup.setup_status_service import CompanySetupStatusService


def test_calculate_progress_uses_completed_required_steps() -> None:
    steps = {
        "company": True,
        "numberSeries": True,
        "supplier": False,
        "customer": False,
        "material": False,
        "product": False,
        "bom": False,
        "openingStock": False,
    }

    assert CompanySetupStatusService.calculate_progress(steps) == 25


def test_calculate_progress_returns_zero_for_no_completed_steps() -> None:
    steps = {
        "company": False,
        "numberSeries": False,
        "supplier": False,
        "customer": False,
        "material": False,
        "product": False,
        "bom": False,
        "openingStock": False,
    }

    assert CompanySetupStatusService.calculate_progress(steps) == 0
