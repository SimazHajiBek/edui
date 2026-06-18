# # # utils.py


from .gemini_client import GeminiClient
from django.conf import settings
import datetime
import json

def process_lesson_logic(prompt):
    """
    إرسال prompt لتوليد خطة درس باستخدام AI.
    ترجع النتيجة كما هي من النموذج بدون تعديل.
    """
    try:
        # استدعاء الكلاس
        client = GeminiClient(api_key=settings.GEMINI_API_KEY)

        response = client.generate_text(prompt)

        # التحقق من الخطأ
        if isinstance(response, dict) and response.get("status") == "error":
            return response

        return {
            "status": "success",
            "analysis": response
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def process_image_logic(image_url, prompt=None):
    try:
        if isinstance(image_url, str) and image_url.startswith('/'):
            image_url = f"http://127.0.0.1:8000{image_url}"

        # استدعاء الكلاس
        client = GeminiClient(api_key=settings.GEMINI_API_KEY)

        gemini_response = client.analyze_image(image_url, prompt=prompt)
        mistakes = gemini_response.get("mistakes") or []

        # إذا حدث خطأ داخل الكلاس نرجعه فوراً
        if isinstance(gemini_response, dict) and gemini_response.get("status") == "error":
            return gemini_response

        #return {"status": "success", "analysis": analysis}
        return {
            "status": "success",
            "analysis": gemini_response,
            "mistakes": mistakes
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}



def process_image_for_corrections(img_url, prompt=None):
    """
    إرسال الصورة إلى AI للتحقق من تصحيح الأخطاء.
    ترجع النتيجة مباشرة كما طلبها prompt بدون أي حقول إضافية.
    """
    try:
        client = GeminiClient(api_key=settings.GEMINI_API_KEY)
        response = client.analyze_image(img_url, prompt=prompt)

        # التحقق من وجود خطأ
        if isinstance(response, dict) and response.get("status") == "error":
            return response

        # إعادة النتيجة كما هي من AI
        return {"status": "success", "analysis": response}

    except Exception as e:
        return {"status": "error", "message": str(e)}
    


def process_comment_logic(image_url, teacher_comment, prompt=None):
    try:
        # استدعاء الكلاس
        client = GeminiClient(api_key=settings.GEMINI_API_KEY)

        # التأكد من أن الرابط كامل إذا كان يبدأ بـ / (للاختبار المحلي)
        if isinstance(image_url, str) and image_url.startswith('/'):
            image_url = f"http://127.0.0.1:8000{image_url}"

        # إذا لم يتم تمرير برومبت، يمكن إنشاء برومبت افتراضي
        if prompt is None:
            prompt = f"""
You are an expert teacher.

Analyze the student's assignment (image URL: {image_url}) and the teacher's comment:

Teacher Comment: "{teacher_comment}"

Return strictly valid JSON with the following fields:

{{
  "student_score": number (0-100),  
  "teacher_comment_score_quality": number (0-100), 
  "clarity": "Excellent | Good | Average | Poor",
  "constructiveness": "Excellent | Good | Average | Poor",
  "mistakes_in_feedback": [
      {{
          "text": "incorrect or unhelpful part of the comment",
          "explanation": "why it is considered a mistake"
      }}
  ],
  "recommendations": "One clear actionable advice to improve the teacher's feedback"
}}

Return JSON only, do not include any text outside JSON.
"""

        # إرسال البيانات إلى API
        gemini_response = client.analyze_image(image_url, prompt=prompt)

        # التحقق من وجود خطأ
        if isinstance(gemini_response, dict) and gemini_response.get("status") == "error":
            return gemini_response

        # إعادة النتيجة مباشرة
        return {"status": "success", "analysis": gemini_response}

    except Exception as e:
        return {"status": "error", "message": str(e)}
    

def process_yearly_summary_logic(yearly_summary, prompt=None):
    """
    إرسال ملخص سنوي للمعلم إلى Gemini API لتحليل الأداء السنوي.
    yearly_summary: قائمة من التقييمات المختصرة (JSON)
    prompt: نص توجيهي مخصص، إذا لم يُمرر يتم توليد برومبت افتراضي
    """
    try:
        client = GeminiClient(api_key=settings.GEMINI_API_KEY)

        # إذا لم يتم تمرير برومبت، يتم إنشاء برومبت افتراضي
        if prompt is None:
            prompt = f"""
You are an expert school inspector analyzing teacher performance over the year.

The following data is a summary of the teacher's evaluations (most recent 30–35 assignments):

{json.dumps(yearly_summary, ensure_ascii=False, indent=2)}

Your tasks:
1. Evaluate the teacher's overall performance in clarity and constructiveness of feedback.
2. Highlight recurring mistakes or issues in feedback.
3. Identify trends or improvements across the year.
4. Evaluate the teacher using the following additional criteria:
   - Presentation / organization of student work
   - Feedback quality
   - Student response to feedback
   - Peer/self-assessment
   - Challenge provided to students
   - Attainment
   - Progress
   - Writing quality
5. Provide actionable recommendations to improve the teacher's feedback and overall performance.

Return strictly valid JSON in the following format:

{{
    "overall_evaluation": {{
        "clarity": "Excellent | Good | Average | Poor",
        "constructiveness": "Excellent | Good | Average | Poor"
    }},
    "recurring_issues": [
        {{"text": "...", "occurrences": number}}
    ],
    "trends": "Summary of improvements or declines over the year",
    "presentation": "Outstanding | Very good | Good | Acceptable | Weak",
    "feedback_quality": "Excellent | Good | Average | Poor",
    "student_response": "High | Medium | Low",
    "peer_self_assessment": "Excellent | Good | Average | Poor",
    "challenge": "High | Medium | Low",
    "attainment": "Above | In line | Below | Weak",
    "progress": "Better than expected | Expected | Limited | Weak",
    "writing_quality": "Excellent | Good | Average | Poor",
    "recommendations": "One clear actionable advice"
}}

Return JSON only.
"""


        # إرسال البيانات للـ AI
        ai_result = client.analyze_json(data_json=yearly_summary, prompt=prompt)

        if isinstance(ai_result, dict) and ai_result.get("status") == "error":
            return ai_result

        return {"status": "success", "analysis": ai_result}

    except Exception as e:
        return {"status": "error", "message": str(e)}