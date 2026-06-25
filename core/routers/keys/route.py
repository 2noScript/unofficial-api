from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from core.session import generate_api_key, list_api_keys, revoke_api_key

router = APIRouter(tags=["API Keys"])

class KeyGenerateRequest(BaseModel):
    name: str = Field(default="", description="Optional friendly name for the API key")

class KeyGenerateResponse(BaseModel):
    api_key: str = Field(..., description="The generated API key")
    name: str = Field(..., description="The name assigned to the key")

class KeyRevokeRequest(BaseModel):
    api_key: str = Field(..., description="The complete API key to revoke")

class KeyRevokeResponse(BaseModel):
    status: str = Field("revoked", description="Status of revocation")
    api_key: str = Field(..., description="The revoked API key")

class KeyInfo(BaseModel):
    key: str = Field(..., description="Masked API key (e.g. ua-xxxxx...)")
    name: str = Field(..., description="The key's friendly name")
    created_at: str = Field(..., description="Creation date ISO string")
    is_active: bool = Field(..., description="True if key is active")
    last_used: str = Field(default="", description="Last usage date ISO string if used")

class KeyListResponse(BaseModel):
    keys: list[KeyInfo]

@router.post("/generate", response_model=KeyGenerateResponse, summary="Generate a new API key")
def generate_key(body: KeyGenerateRequest):
    try:
        api_key = generate_api_key(body.name)
        from core.session.api_key import _load_keys
        data = _load_keys()
        name = data.get("keys", {}).get(api_key, {}).get("name", body.name)
        return KeyGenerateResponse(api_key=api_key, name=name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate API key: {str(e)}"
        )

@router.get("", response_model=KeyListResponse, summary="List all API keys")
def list_keys():
    try:
        keys = list_api_keys()
        return KeyListResponse(keys=keys)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list API keys: {str(e)}"
        )

@router.post("/revoke", response_model=KeyRevokeResponse, summary="Revoke (deactivate) an API key")
def revoke_key(body: KeyRevokeRequest):
    try:
        success = revoke_api_key(body.api_key)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found or already inactive"
            )
        return KeyRevokeResponse(status="revoked", api_key=body.api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke API key: {str(e)}"
        )
