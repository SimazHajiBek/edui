import os
import logging
from django.core.management.base import BaseCommand
from django.db.models import Q
import easyocr
from dashboard.models import UploadedImage, OCRResult

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='process_images.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

class Command(BaseCommand):
    help = 'OCR ONLY: Extract raw text from images and store it without analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--image_id',
            type=int,
            help='Process only this uploaded image (optional)'
        )

    def handle(self, *args, **options):
        reader = easyocr.Reader(['en', 'ar'])
        image_id = options.get('image_id')

        if image_id:
            images = UploadedImage.objects.filter(id=image_id)
        else:
            images = UploadedImage.objects.filter(
                Q(ocrresult__isnull=True) | Q(ocrresult__processed=False)
            )

        for image_obj in images:
            if not image_obj.image:
                logger.warning(f"Image object {image_obj.id} has no file associated")
                continue

            img_path = image_obj.image.path
            if not os.path.exists(img_path):
                logger.warning(f"File does not exist on disk: {img_path}")
                continue

            logger.info(f"OCR processing image: {img_path}")

            try:
                ocr_result = reader.readtext(img_path)
            except Exception as e:
                logger.error(f"OCR failed for {img_path}: {e}")
                continue

            extracted_data = []
            confidences = []

            for bbox, text, prob in ocr_result:
                extracted_data.append({
                    "text": text,
                    "bbox": bbox,
                    "confidence": prob
                })
                confidences.append(prob)

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            OCRResult.objects.update_or_create(
                image=image_obj,
                defaults={
                    "extracted_text": extracted_data,
                    "confidence": avg_confidence,
                    "processed": True
                }
            )

            logger.info(f"OCR saved for image {image_obj.id} (confidence={avg_confidence:.2f})")
