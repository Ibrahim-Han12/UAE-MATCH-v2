from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserPhotoBase(BaseModel):
    display_order: Optional[int] = Field(None, description="显示顺序")
    is_primary: Optional[bool] = Field(None, description="是否为主照片")


class UserPhotoCreate(UserPhotoBase):
    file_path: str = Field(..., description="文件存储路径")
    file_url: str = Field(..., description="访问URL")
    file_name: Optional[str] = Field(None, description="原始文件名")
    file_size: Optional[int] = Field(None, description="文件大小")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")


class UserPhotoUpdate(BaseModel):
    display_order: Optional[int] = None
    is_primary: Optional[bool] = None


class UserPhotoRead(BaseModel):
    id: int
    user_id: int
    file_path: str
    file_url: str
    file_name: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    display_order: int
    is_primary: bool
    is_verified: bool
    status: str
    rejection_reason: Optional[str]
    width: Optional[int]
    height: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PhotoUploadResponse(BaseModel):
    photo: UserPhotoRead
    message: str = "照片上传成功"


class PhotoReorderRequest(BaseModel):
    photo_ids: list[int] = Field(..., description="照片ID列表，按顺序排列")
