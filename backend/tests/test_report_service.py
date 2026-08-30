from unittest.mock import Mock

from app.core.security import CurrentUser
from app.schemas.report import ReportFolderItem, ReportFolderUpdateRequest
from app.services.report_service import ReportService


def test_update_folder_explicit_null_moves_to_root():
    service = ReportService.__new__(ReportService)
    service.current_user = CurrentUser(id=7, username="user", display_name="用户", roles=["user"])
    service.repository = Mock()
    service.repository.folder_exists.return_value = True
    expected = ReportFolderItem(
        id=12,
        name="目录",
        parent_id=None,
        sort_order=0,
        report_count=0,
        created_at="2025-01-01T00:00:00",
        updated_at="2025-01-01T00:00:00",
    )
    service.repository.update_folder.return_value = expected
    request = ReportFolderUpdateRequest.model_validate({"parent_id": None})

    result = service.update_folder(12, request)

    assert result is expected
    service.repository.update_folder.assert_called_once_with(
        12,
        None,
        None,
        None,
        parent_id_provided=True,
    )
