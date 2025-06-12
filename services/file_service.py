import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.avatar_dir = self.upload_dir / "avatars"
        self.avatar_dir.mkdir(parents=True, exist_ok=True)

    async def save_avatar(self, file: UploadFile, user_id: int) -> str:
        """Save user avatar and return URL"""
        try:
            # Generate unique filename
            file_extension = file.filename.split(".")[-1].lower()
            filename = f"{user_id}_{uuid.uuid4().hex}.{file_extension}"
            file_path = self.avatar_dir / filename

            # Save uploaded file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Resize image if needed
            await self._resize_avatar(file_path)

            # Return URL (adjust based on your serving setup)
            return f"/uploads/avatars/{filename}"

        except Exception as e:
            logger.error(f"Error saving avatar: {e}")
            raise

    async def _resize_avatar(self, file_path: Path, max_size: tuple = (300, 300)):
        """Resize avatar image to max dimensions"""
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Resize maintaining aspect ratio
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(file_path, "JPEG", quality=85)

        except Exception as e:
            logger.error(f"Error resizing avatar: {e}")
            raise
