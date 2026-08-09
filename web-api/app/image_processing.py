import io

from PIL import Image, ImageOps, UnidentifiedImageError


class InvalidImageError(ValueError):
    pass


def compress_image(data: bytes) -> tuple[bytes, str]:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("Uploaded file is not a valid image") from exc

    original_format = image.format
    image = ImageOps.exif_transpose(image)

    buf = io.BytesIO()
    if original_format == "JPEG":
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        # exif_transpose()/convert() return a fresh Image whose `.format` isn't carried
        # over, but `quality="keep"` reads `image.format` directly to decide whether
        # reusing the original quantization tables is legal, so it must be restored here.
        image.format = "JPEG"
        image.save(buf, format="JPEG", quality="keep", optimize=True)
        extension = ".jpg"
    else:
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        image.save(buf, format="WEBP", lossless=True)
        extension = ".webp"

    return buf.getvalue(), extension
