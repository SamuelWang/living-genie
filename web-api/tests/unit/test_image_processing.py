import io

import pytest
from PIL import Image

from app.image_processing import InvalidImageError, compress_image


def _png_bytes(size: tuple[int, int] = (8, 6), color: tuple[int, int, int] = (200, 50, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(
    size: tuple[int, int] = (8, 6), color: tuple[int, int, int] = (10, 220, 30)
) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def test_png_input_becomes_lossless_webp_with_identical_pixels():
    source = Image.new("RGB", (12, 9), (30, 60, 90))
    buf = io.BytesIO()
    source.save(buf, format="PNG")

    processed, extension = compress_image(buf.getvalue())

    assert extension == ".webp"
    output = Image.open(io.BytesIO(processed))
    assert output.format == "WEBP"
    assert list(output.convert("RGB").getdata()) == list(source.convert("RGB").getdata())


def test_jpeg_input_stays_jpeg():
    processed, extension = compress_image(_jpeg_bytes())

    assert extension == ".jpg"
    output = Image.open(io.BytesIO(processed))
    assert output.format == "JPEG"


def test_exif_rotated_source_is_transposed_and_exif_stripped():
    source = Image.new("RGB", (10, 4), (255, 0, 0))
    exif = Image.Exif()
    exif[274] = 6  # Orientation: rotate 270 CW (i.e. rotate 90 CCW to correct)
    buf = io.BytesIO()
    source.save(buf, format="JPEG", exif=exif)

    processed, _ = compress_image(buf.getvalue())

    output = Image.open(io.BytesIO(processed))
    # Orientation 6 means the raw pixels are stored rotated 90 CW relative to
    # how the image should be displayed, so exif_transpose swaps the axes.
    assert output.size == (source.size[1], source.size[0])
    assert not output.getexif()


def test_non_image_bytes_raise_invalid_image_error():
    with pytest.raises(InvalidImageError):
        compress_image(b"this is definitely not an image")
