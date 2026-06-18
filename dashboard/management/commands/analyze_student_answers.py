from django.core.management.base import BaseCommand
from dashboard.models import StudentAnswer, StudentErrors

class Command(BaseCommand):
    help = "Compare student answers with correct answers and assign score/errors"

    def add_arguments(self, parser):
        parser.add_argument('--image_id', type=int, help='Analyze answers from this image only')

    def handle(self, *args, **options):
        image_id = options.get('image_id')

        if image_id:
            answers = StudentAnswer.objects.filter(
                student_exam__image__id=image_id,
                score__isnull=True
            )

        else:
            answers = StudentAnswer.objects.filter(score__isnull=True)

        for ans in answers:
            question = ans.question
            correct_answer = question.correct_answer

            if not correct_answer:
                continue

            student_text = ans.answer_text.strip()
            if student_text == correct_answer:
                ans.is_correct = True
                ans.score = question.max_score
            else:
                ans.is_correct = False
                ans.score = 0

                StudentErrors.objects.get_or_create(
                    student=ans.student_exam.student,
                    question=question,
                    defaults={"error_type": "Wrong answer"}
                )

            ans.save()
