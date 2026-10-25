import io
import os
import warnings
import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = int(os.environ.get('HTR_MAX_UPLOAD_MB', 50)) * 1024 * 1024
MAX_PIXELS = int(os.environ.get('HTR_MAX_MEGAPIXELS', 100)) * 1_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def validate_image(content: bytes):
    if not content or len(content) > MAX_BYTES:
        raise ValueError(f'Choose a PNG or JPEG smaller than {MAX_BYTES // 1024 // 1024} MiB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                if source.format not in ('JPEG', 'PNG'):
                    raise ValueError('Only PNG and JPEG images are supported.')
                if source.width * source.height > MAX_PIXELS:
                    raise ValueError(f'Image exceeds the {MAX_PIXELS // 1_000_000} megapixel limit.')
                source.load()
                image = ImageOps.exif_transpose(source).convert('RGBA')
                background = Image.new('RGBA', image.size, 'white')
                return Image.alpha_composite(background, image).convert('RGB')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError('This image cannot be decoded safely. Try exporting it as PNG or JPEG.') from exc


def prepare(image, settings):
    """Transform maps EXIF-normalized original pixels to prepared-page pixels."""
    rgb = np.asarray(image)
    h, w = rgb.shape[:2]
    transform = np.eye(3)
    if settings.corners:
        points = np.array([(x * (w - 1), y * (h - 1)) for x, y in settings.corners], np.float32)
        if not cv2.isContourConvex(points.astype(np.int32)) or abs(cv2.contourArea(points)) < w * h * 0.01:
            raise ValueError('Page corners must form a non-crossing rectangle covering at least 1% of the image.')
        tl, tr, br, bl = points
        dw = max(2, int(max(np.linalg.norm(tr-tl), np.linalg.norm(br-bl))))
        dh = max(2, int(max(np.linalg.norm(bl-tl), np.linalg.norm(br-tr))))
        transform = cv2.getPerspectiveTransform(points, np.float32([[0,0],[dw-1,0],[dw-1,dh-1],[0,dh-1]]))
        rgb = cv2.warpPerspective(rgb, transform, (dw, dh), borderValue=(255,255,255))
    if settings.rotation:
        for _ in range(settings.rotation // 90):
            ph, pw = rgb.shape[:2]
            matrix = np.array([[0,-1,ph-1],[1,0,0],[0,0,1]], float)
            rgb = cv2.rotate(rgb, cv2.ROTATE_90_CLOCKWISE)
            transform = matrix @ transform
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    sample = cv2.resize(gray, (max(1, int(gray.shape[1] * min(1, 1800 / max(gray.shape)))),
                               max(1, int(gray.shape[0] * min(1, 1800 / max(gray.shape))))))
    notes = []
    if float(sample.std()) < 18:
        notes.append('Low contrast: try Enhanced contrast or photograph the page in even light.')
    if cv2.Laplacian(sample, cv2.CV_64F).var() < 35:
        notes.append('The page may be blurred. A sharper photograph can improve recognition.')
    if settings.deskew:
        mask = cv2.threshold(sample, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        # Hough segments avoid interpreting the page's aspect ratio as text skew.
        found = cv2.HoughLinesP(mask, 1, np.pi / 1800, 70,
                               minLineLength=max(40, sample.shape[1] // 8), maxLineGap=20)
        angles = [] if found is None else [np.degrees(np.arctan2(y2-y1,x2-x1))
                                          for x1,y1,x2,y2 in np.asarray(found).reshape(-1,4)]
        angles = [a for a in angles if abs(a) <= 12]
        if angles:
            angle = float(np.median(angles))
            if abs(angle) > 0.2:
                ph, pw = gray.shape
                affine = cv2.getRotationMatrix2D((pw / 2, ph / 2), angle, 1)
                cosine,sine=abs(affine[0,0]),abs(affine[0,1])
                nw,nh=int(np.ceil(pw*cosine+ph*sine)),int(np.ceil(ph*cosine+pw*sine))
                affine[0,2]+=(nw-pw)/2
                affine[1,2]+=(nh-ph)/2
                rgb = cv2.warpAffine(rgb, affine, (nw,nh), borderValue=(255,255,255))
                transform = np.vstack([affine,[0,0,1]]) @ transform
    if settings.preprocessing == 'enhanced':
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        lab[:,:,0] = cv2.createCLAHE(clipLimit=2, tileGridSize=(8,8)).apply(lab[:,:,0])
        rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    return Image.fromarray(rgb), transform.tolist(), notes


def crop_line(image, polygon, padding):
    points = np.asarray(polygon, np.float32)
    if not np.isfinite(points).all():
        raise ValueError('Line coordinates must be finite.')
    x1, y1 = np.floor(points.min(axis=0) - padding).astype(int)
    x2, y2 = np.ceil(points.max(axis=0) + padding).astype(int)
    x1, y1, x2, y2 = max(0,x1), max(0,y1), min(image.width,x2), min(image.height,y2)
    if x2 <= x1 or y2 <= y1:
        raise ValueError('A line region is outside the page or has no area.')
    crop = image.crop((x1,y1,x2,y2))
    # Whiten surrounding regions while preserving every pixel inside the polygon.
    mask = np.zeros((y2-y1,x2-x1), np.uint8)
    cv2.fillPoly(mask, [np.rint(points-[x1,y1]).astype(np.int32)], 255)
    if padding:
        mask = cv2.dilate(mask, np.ones((2*padding+1,2*padding+1),np.uint8))
    pixels = np.array(crop)
    pixels[mask == 0] = 255
    return Image.fromarray(pixels)


def split_long_line(image, max_ratio=12):
    """Bound visual compression; split near low-ink columns without dropping pixels."""
    if image.width / image.height <= max_ratio:
        return [image]
    gray = np.asarray(image.convert('L'))
    ink = (gray < 180).mean(axis=0)
    width = max(32, int(image.height * max_ratio))
    crops, start = [], 0
    while image.width - start > width:
        lo, hi = start + int(width * .65), min(image.width, start + width)
        cut = lo + int(np.argmin(ink[lo:hi]))
        crops.append(image.crop((start,0,cut,image.height)))
        start = cut
    crops.append(image.crop((start,0,image.width,image.height)))
    return crops


def rectify_line(image,line,padding):
    """Unbend learned baselines at original resolution; manual boxes use masked crops."""
    if line.baseline and len(line.baseline)>=2:
        from kraken.containers import BaselineLine, Segmentation
        from kraken.lib.segmentation import extract_polygons
        record=BaselineLine(id=line.id,baseline=[tuple(map(round,p)) for p in line.baseline],
                            boundary=[tuple(map(round,p)) for p in line.polygon])
        bounds=Segmentation(type='baselines',imagename='',text_direction='horizontal-lr',
                            script_detection=False,lines=[record])
        # Kraken masks outside ink with zero; invert around rectification to preserve white paper.
        rectified,_=next(extract_polygons(ImageOps.invert(image.convert('RGB')),bounds))
        return ImageOps.expand(ImageOps.invert(rectified),border=padding,fill='white')
    return crop_line(image,line.polygon,padding)
