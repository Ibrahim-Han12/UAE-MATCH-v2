"""
照片上传和管理API
"""
import os
import uuid
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.models.user_photo import UserPhoto
from app.schemas.photo import (
    PhotoReorderRequest,
    PhotoUploadResponse,
    UserPhotoRead,
    UserPhotoUpdate,
)

router = APIRouter(prefix="/photos", tags=["photos"])


def _get_photo_path(filename: str) -> Path:
    """获取照片存储路径"""
    return Path(settings.UPLOAD_DIR) / "photos" / filename


def _generate_filename(user_id: int, original_filename: str) -> str:
    """生成唯一文件名"""
    ext = Path(original_filename).suffix.lower()
    unique_id = str(uuid.uuid4())
    return f"{user_id}_{unique_id}{ext}"


async def _save_photo(file: UploadFile, user_id: int) -> tuple[str, str, int, dict]:
    """
    保存照片文件
    返回: (file_path, file_url, file_size, metadata)
    """
    # 验证文件类型
    if file.content_type not in settings.ALLOWED_PHOTO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型，仅支持: {', '.join(settings.ALLOWED_PHOTO_TYPES)}",
        )

    # 读取文件内容
    contents = await file.read()
    file_size = len(contents)

    # 验证文件大小
    if file_size > settings.MAX_PHOTO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件太大，最大支持 {settings.MAX_PHOTO_SIZE / 1024 / 1024}MB",
        )

    # 生成文件名
    filename = _generate_filename(user_id, file.filename or "photo.jpg")
    file_path = _get_photo_path(filename)

    # 保存文件
    with open(file_path, "wb") as f:
        f.write(contents)

    # 获取图片尺寸
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            metadata = {"width": width, "height": height}
    except Exception:
        metadata = {}

    # 生成访问URL（开发环境使用相对路径，生产环境需要配置CDN）
    file_url = f"/api/v1/photos/file/{filename}"

    return str(file_path), file_url, file_size, metadata


@router.post("/upload", response_model=PhotoUploadResponse)
async def upload_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    上传照片
    - 支持 JPEG, PNG, WebP
    - 最大 10MB
    - 每个用户最多 9 张照片
    """
    # 检查照片数量限制
    existing_count = (
        db.query(UserPhoto)
        .filter(UserPhoto.user_id == current_user.id)
        .filter(UserPhoto.status != "rejected")
        .count()
    )

    if existing_count >= settings.PHOTOS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"最多只能上传 {settings.PHOTOS_PER_USER} 张照片",
        )

    try:
        # 保存文件
        file_path, file_url, file_size, metadata = await _save_photo(file, current_user.id)

        # 创建数据库记录
        photo = UserPhoto(
            user_id=current_user.id,
            file_path=file_path,
            file_url=file_url,
            file_name=file.filename,
            file_size=file_size,
            mime_type=file.content_type,
            width=metadata.get("width"),
            height=metadata.get("height"),
            status="pending",  # 待审核
            display_order=existing_count,  # 默认顺序
        )

        db.add(photo)
        db.commit()
        db.refresh(photo)

        return PhotoUploadResponse(
            photo=UserPhotoRead.model_validate(photo),
            message="照片上传成功，等待审核",
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败: {str(e)}",
        )


@router.get("/me", response_model=List[UserPhotoRead])
def get_my_photos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """获取当前用户的所有照片"""
    photos = (
        db.query(UserPhoto)
        .filter(UserPhoto.user_id == current_user.id)
        .filter(UserPhoto.status != "rejected")  # 不返回被拒绝的照片
        .order_by(UserPhoto.display_order.asc(), UserPhoto.created_at.asc())
        .all()
    )
    return photos


@router.get("/{photo_id}", response_model=UserPhotoRead)
def get_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """获取单张照片信息"""
    photo = (
        db.query(UserPhoto)
        .filter(UserPhoto.id == photo_id, UserPhoto.user_id == current_user.id)
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在"
        )

    return photo


@router.get("/file/{filename}")
async def get_photo_file(filename: str):
    """获取照片文件（用于前端显示）"""
    file_path = _get_photo_path(filename)

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在"
        )

    return FileResponse(
        file_path,
        media_type="image/jpeg",  # 可以根据实际文件类型调整
    )


@router.put("/{photo_id}", response_model=UserPhotoRead)
def update_photo(
    photo_id: int,
    photo_update: UserPhotoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """更新照片信息（排序、设置主照片）"""
    photo = (
        db.query(UserPhoto)
        .filter(UserPhoto.id == photo_id, UserPhoto.user_id == current_user.id)
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在"
        )

    # 如果设置为主照片，取消其他主照片
    if photo_update.is_primary:
        db.query(UserPhoto).filter(
            UserPhoto.user_id == current_user.id,
            UserPhoto.id != photo_id,
        ).update({"is_primary": False})
        photo.is_primary = True

    # 更新其他字段
    if photo_update.display_order is not None:
        photo.display_order = photo_update.display_order

    db.commit()
    db.refresh(photo)

    return photo


@router.post("/reorder", response_model=List[UserPhotoRead])
def reorder_photos(
    reorder_request: PhotoReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """重新排序照片"""
    # 验证所有照片都属于当前用户
    photos = (
        db.query(UserPhoto)
        .filter(
            UserPhoto.id.in_(reorder_request.photo_ids),
            UserPhoto.user_id == current_user.id,
        )
        .all()
    )

    if len(photos) != len(reorder_request.photo_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="包含不属于您的照片"
        )

    # 更新顺序
    for index, photo_id in enumerate(reorder_request.photo_ids):
        photo = next(p for p in photos if p.id == photo_id)
        photo.display_order = index
        photo.is_primary = index == 0  # 第一张为主照片

    db.commit()

    # 返回更新后的照片列表
    return get_my_photos(db, current_user)


@router.delete("/{photo_id}")
def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """删除照片"""
    photo = (
        db.query(UserPhoto)
        .filter(UserPhoto.id == photo_id, UserPhoto.user_id == current_user.id)
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在"
        )

    # 删除文件
    try:
        if os.path.exists(photo.file_path):
            os.remove(photo.file_path)
    except Exception:
        pass  # 文件删除失败不影响数据库删除

    # 删除数据库记录
    db.delete(photo)
    db.commit()

    return {"message": "照片已删除"}
