from fastapi import Request
from fastapi.responses import JSONResponse
from notebooklm.types import SharePermission, ShareViewLevel

from app.schemas import (
    NLMSharingAddUserRequest,
    NLMSharingRemoveUserRequest,
    NLMSharingSetPublicRequest,
    NLMSharingSetViewLevelRequest,
    NLMSharingUpdateUserRequest,
    NLMSharingUserResponse,
    NLMShareStatusResponse,
)

from .router import router
from .helpers import _require_client


def _share_status_to_dict(status):
    return {
        "notebook_id": status.notebook_id,
        "is_public": status.is_public,
        "access": int(status.access) if hasattr(status.access, "value") else int(status.access or 0),
        "view_level": int(status.view_level.value) if hasattr(status.view_level, "value") else int(status.view_level or 0),
        "shared_users": [
            {
                "email": u.email,
                "permission": int(u.permission.value) if hasattr(u.permission, "value") else int(u.permission or 3),
                "display_name": u.display_name,
                "avatar_url": u.avatar_url,
            }
            for u in (status.shared_users or [])
        ],
        "share_url": status.share_url,
    }


def _parse_permission(val: int) -> SharePermission:
    if val == 2:
        return SharePermission.EDITOR
    return SharePermission.VIEWER


def _parse_view_level(val: int) -> ShareViewLevel:
    if val == 1:
        return ShareViewLevel.CHAT_ONLY
    return ShareViewLevel.FULL_NOTEBOOK


@router.get(
    "/notebooks/{notebook_id}/sharing/status",
    summary="Get current sharing configuration",
)
async def get_sharing_status(notebook_id: str, request: Request):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        status = await client.sharing.get_status(notebook_id)
        return _share_status_to_dict(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/sharing/public",
    summary="Enable or disable public link sharing",
)
async def set_sharing_public(
    notebook_id: str,
    body: NLMSharingSetPublicRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        status = await client.sharing.set_public(notebook_id, body.public)
        return _share_status_to_dict(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/sharing/view-level",
    summary="Set what viewers can access",
)
async def set_sharing_view_level(
    notebook_id: str,
    body: NLMSharingSetViewLevelRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        level = _parse_view_level(body.level)
        status = await client.sharing.set_view_level(notebook_id, level)
        return _share_status_to_dict(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/notebooks/{notebook_id}/sharing/users",
    summary="Share notebook with a user",
    status_code=201,
)
async def add_sharing_user(
    notebook_id: str,
    body: NLMSharingAddUserRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        permission = _parse_permission(body.permission)
        status = await client.sharing.add_user(
            notebook_id,
            body.email,
            permission=permission,
            notify=body.notify,
            welcome_message=body.welcome_message,
        )
        return _share_status_to_dict(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.patch(
    "/notebooks/{notebook_id}/sharing/users",
    summary="Update a user's sharing permission",
)
async def update_sharing_user(
    notebook_id: str,
    body: NLMSharingUpdateUserRequest,
    request: Request,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        permission = _parse_permission(body.permission)
        status = await client.sharing.update_user(notebook_id, body.email, permission)
        return _share_status_to_dict(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete(
    "/notebooks/{notebook_id}/sharing/users",
    summary="Remove a user's access to the notebook",
)
async def remove_sharing_user(
    notebook_id: str,
    request: Request,
    email: str,
):
    try:
        client = await _require_client(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503)

    try:
        status = await client.sharing.remove_user(notebook_id, email)
        return _share_status_to_dict(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
