from PIL import Image, ImageDraw


def draw_smooth_ellipse(base_img, bbox, fill=None, outline=None, width=1, scale=4):
    """Draw an anti-aliased ellipse on top of `base_img`.

    This function creates a larger temporary overlay at `scale` times the
    base size, draws the ellipse there, downsamples with LANCZOS and
    composites it onto the base image. This produces much smoother edges.

    Args:
        base_img (PIL.Image): RGBA image to draw onto. Returned image is a new
            Image object (alpha-composited).
        bbox (sequence): [x0, y0, x1, y1] bounding box in base image coordinates.
        fill (tuple|str): Fill color (RGBA tuple or PIL color).
        outline (tuple|str): Outline color.
        width (int): Outline width in base-image pixels.
        scale (int): Supersampling factor. 3-6 is usually good. Default 4.

    Returns:
        PIL.Image: New RGBA image with the ellipse composited.
    """
    if base_img.mode != 'RGBA':
        base_img = base_img.convert('RGBA')

    w, h = base_img.size
    # Create large transparent overlay
    overlay_large = Image.new('RGBA', (w * scale, h * scale), (0, 0, 0, 0))
    draw_large = ImageDraw.Draw(overlay_large)

    x0, y0, x1, y1 = bbox
    bbox_large = [int(x0 * scale), int(y0 * scale), int(x1 * scale), int(y1 * scale)]

    if fill:
        draw_large.ellipse(bbox_large, fill=fill)

    if outline and width and width > 0:
        draw_large.ellipse(bbox_large, outline=outline, width=max(1, int(width * scale)))

    # Downsample overlay to original size with LANCZOS (antialiasing)
    overlay_small = overlay_large.resize((w, h), Image.Resampling.LANCZOS)

    # Composite overlay onto base image
    result = Image.alpha_composite(base_img, overlay_small)
    return result
