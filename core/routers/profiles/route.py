from typing import Literal
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from core.profile import (
    create_profile,
    list_profiles,
    get_profile,
    update_profile,
    delete_profile
)

router = APIRouter(tags=["Profiles"])


class ProfileCreateRequest(BaseModel):
    type: Literal["deepseek", "gemini"] = Field(..., description="Type of profile: 'deepseek' or 'gemini'")
    name: str = Field(..., description="Friendly name for the profile")
    token: str | None = Field(default=None, description="Auth token (required for 'deepseek')")
    cookie: str | None = Field(default=None, description="Cookie string (required for 'gemini')")
    is_active: bool = Field(default=True, description="Whether the profile is active")


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, description="Updated friendly name")
    token: str | None = Field(default=None, description="Updated token (for deepseek)")
    cookie: str | None = Field(default=None, description="Updated cookie (for gemini)")
    is_active: bool | None = Field(default=None, description="Updated active status")


class ProfileResponse(BaseModel):
    id: str = Field(..., description="Unique profile ID")
    type: str = Field(..., description="Profile type ('deepseek' or 'gemini')")
    name: str = Field(..., description="Friendly profile name")
    token: str | None = Field(default=None, description="Auth token if deepseek profile")
    cookie: str | None = Field(default=None, description="Cookie string if gemini profile")
    is_active: bool = Field(..., description="Active status")
    total_requests: int = Field(default=0, description="Total requests processed by profile")
    request_counts: dict[str, dict[str, int]] = Field(
        default_factory=dict, description="Request counts grouped by date (YYYY-MM-DD) and hour (HH)"
    )
    created_at: str = Field(..., description="Creation date ISO string")
    updated_at: str = Field(..., description="Last updated date ISO string")



class ProfileListResponse(BaseModel):
    profiles: list[ProfileResponse]


class ProfileDeleteResponse(BaseModel):
    status: str = Field("deleted", description="Status of deletion")
    id: str = Field(..., description="ID of deleted profile")


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED, summary="Create a new profile")
def create_new_profile(body: ProfileCreateRequest):
    if body.type == "deepseek" and not body.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'token' is required for DeepSeek profile."
        )
    if body.type == "gemini" and not body.cookie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'cookie' is required for Gemini profile."
        )

    try:
        profile = create_profile(
            profile_type=body.type,
            name=body.name,
            token=body.token,
            cookie=body.cookie,
            is_active=body.is_active
        )
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {str(e)}"
        )


@router.get("", response_model=ProfileListResponse, summary="List all profiles")
def get_profiles(type: Literal["deepseek", "gemini"] | None = Query(None, description="Filter profiles by type")):
    try:
        profiles = list_profiles(profile_type=type)
        return ProfileListResponse(profiles=profiles)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list profiles: {str(e)}"
        )


@router.get("/{profile_id}", response_model=ProfileResponse, summary="Get profile by ID")
def get_profile_by_id(profile_id: str):
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID '{profile_id}' not found."
        )
    return profile


@router.put("/{profile_id}", response_model=ProfileResponse, summary="Update profile by ID")
def update_profile_by_id(profile_id: str, body: ProfileUpdateRequest):
    existing = get_profile(profile_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID '{profile_id}' not found."
        )

    try:
        updated = update_profile(
            profile_id=profile_id,
            name=body.name,
            token=body.token,
            cookie=body.cookie,
            is_active=body.is_active
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID '{profile_id}' not found."
            )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.delete("/{profile_id}", response_model=ProfileDeleteResponse, summary="Delete profile by ID")
def delete_profile_by_id(profile_id: str):
    deleted = delete_profile(profile_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID '{profile_id}' not found."
        )
    return ProfileDeleteResponse(status="deleted", id=profile_id)
