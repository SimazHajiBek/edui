# # dashboard/management/commands/link_ocr_to_questions.py

from django.core.management.base import BaseCommand
from dashboard.models import OCRResult, ExamQuestions, StudentAnswer, StudentExam
from rapidfuzz import fuzz

class Command(BaseCommand):
    help = "Link OCR text regions to exam questions (NO GRADING)"

    def add_arguments(self, parser):
        parser.add_argument('--image_id', type=int, help='Process only this image')

    def handle(self, *args, **options):
        image_id = options.get('image_id')
        if image_id:
            ocr_results = OCRResult.objects.filter(processed=True, image_id=image_id)
        else:
            ocr_results = OCRResult.objects.filter(processed=True)

        for ocr in ocr_results:
            image = ocr.image
            student = getattr(image, "student", None)
            subject = getattr(image, "subject", None)

            if not student or not subject:
                continue

            student_exams = StudentExam.objects.filter(student=student, exam__subject=subject)
            if not student_exams.exists():
                continue

            for student_exam in student_exams:
                questions = ExamQuestions.objects.filter(exam=student_exam.exam)

                for block in ocr.extracted_text:
                    text = ""
                    if isinstance(block, tuple) and len(block) == 3:
                        text = block[1]
                    elif isinstance(block, dict):
                        text = block.get("text", "")
                    else:
                        text = str(block)
                    text = text.strip()
                    if not text:
                        continue

                    best_match = None
                    best_score = 0
                    for q in questions:
                        score = fuzz.partial_ratio(q.question_text, text)
                        if score > best_score and score > 70:
                            best_score = score
                            best_match = q

                    if best_match:
                        answer = StudentAnswer.objects.filter(
                            student_exam=student_exam,
                            question=best_match
                        ).first()

                        if not answer:
                            StudentAnswer.objects.create(
                                student_exam=student_exam,
                                question=best_match,
                                answer_text=text,
                                score=None,
                                is_correct=None
                            )

        self.stdout.write(self.style.SUCCESS("OCR text linked to exam questions successfully."))
