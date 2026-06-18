
import google.generativeai as genai
import json
import PIL.Image
from google.api_core import exceptions
import requests
from io import BytesIO
import PIL.Image
    
class GeminiClient:
    def __init__(self, api_key):
        
        genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def generate_text(self, prompt):
        try:
            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def analyze_image(self, image_url, prompt=None):
        try:
            response = requests.get(image_url)
            response.raise_for_status()  
            img = PIL.Image.open(BytesIO(response.content))
            
            generation_config = {
                "response_mime_type": "application/json",
            }
            img.thumbnail((1024, 1024))

            response = self.model.generate_content(
                contents=[prompt if prompt else "Analyze this image and return JSON", img],
                generation_config=generation_config
            )

            if response.candidates and response.candidates[0].content.parts:
                return json.loads(response.text)
            else:
                return {"status": "error", "message": "Content blocked by safety filters"}

        except exceptions.ResourceExhausted:
            return {"status": "error", "message": "Quota exceeded (429). Wait 60 seconds."}
        except exceptions.PermissionDenied:
            return {"status": "error", "message": "Invalid API Key or Permission denied (401/403)."}
        except Exception as e:
            try:
                cleaned_text = response.text.replace('```json', '').replace('```', '').strip()
                return json.loads(cleaned_text)
            except:
                return {"status": "error", "message": f"URL Image Error: {str(e)}"}  
            
    def analyze_json(self, data_json, prompt=None):
        
        try:
            content_str = json.dumps(data_json, ensure_ascii=False, indent=2)

            if not prompt:
                prompt = f"Analyze the following data and return strictly valid JSON:\n\n{content_str}"

            generation_config = {
                "response_mime_type": "application/json",
            }

            response = self.model.generate_content(
                contents=[prompt,content_str],
                generation_config=generation_config
            )

            if response.candidates and response.candidates[0].content.parts:
                return json.loads(response.text)
            else:
                return {"status": "error", "message": "Content blocked by safety filters"}

        except Exception as e:
            try:
                cleaned_text = response.text.replace('```json', '').replace('```', '').strip()
                return json.loads(cleaned_text)
            except:
                return {"status": "error", "message": f"JSON Analysis Error: {str(e)}"}
            
    