import os
import json
# استيراد الكلاس الذي عدلناه سابقاً
from gemini_client import GeminiClient 

# 1. إعدادات الاختبار
API_KEY = "" 
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
IMAGE_PATH = "test_image.jpg"  # ضع مسار صورة حقيقية موجودة عندك للتجربة

# 2. الـ Prompt الذي استخدمته في Django
TEST_PROMPT = """
You are an intelligent educational assistant. 
Analyze the image and return the result strictly in JSON format:
{
  "score": number,
  "confidence": number,
  "strengths": [],
  "mistakes": [],
  "weaknesses": []
}
"""

def run_test():
    # التأكد من وجود الصورة
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: Image file '{IMAGE_PATH}' not found!")
        return

    print("جاري إرسال الطلب إلى Gemini...")
    
    try:
        # إنشاء الكلاينت
        client = GeminiClient(api_key=API_KEY, api_url=API_URL)
        
        # تنفيذ التحليل
        response = client.analyze_image(IMAGE_PATH, prompt=TEST_PROMPT)
        
        # طباعة النتيجة بشكل منسق
        print("\n--- تم استقبال الرد بنجاح ---")
        print(json.dumps(response, indent=4, ensure_ascii=False))
        
    except Exception as e:
        print(f"\nحدث خطأ أثناء التجربة:")
        print(str(e))

if __name__ == "__main__":
    run_test()