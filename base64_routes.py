# api.py
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import base64
import io
from PIL import Image

router = APIRouter()

@router.post("/convert-image")
async def convert_image_to_base64(file: UploadFile = File(...)):
    """
    Convert an uploaded image to base64 string.
    """
    try:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Optional: basic max-size guard (e.g., 10 MB)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

        base64_string = base64.b64encode(contents).decode("utf-8")
        data_url = f"data:{file.content_type};base64,{base64_string}"

        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "content_type": file.content_type,
            "base64": base64_string,
            "data_url": data_url,
            "size": len(base64_string),  # characters
            "original_bytes": len(contents)
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@router.post("/convert-from-base64")
async def convert_image_from_base64(payload: dict):
    """
    Accepts { "base64_string": "<...>" } and returns decoded image info.
    """
    try:
        base64_string = payload.get("base64_string")
        if not base64_string:
            raise HTTPException(status_code=400, detail="base64_string is required")

        if base64_string.startswith("data:"):
            base64_string = base64_string.split(",", 1)[1]

        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))

        return JSONResponse({
            "success": True,
            "format": image.format,
            "size": image.size,
            "mode": image.mode,
            "data_size": len(image_data)
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing base64: {str(e)}")
