from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from edui.settings import GEMINI_API_KEY
from collections import Counter
from .utils import process_lesson_logic, process_image_logic,process_comment_logic, process_yearly_summary_logic, process_image_for_corrections
from .gemini_client import GeminiClient
import logging
import json
import re


logger = logging.getLogger(__name__)

@csrf_exempt
def generate_lesson_plan(request):
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Only POST allowed"},
            status=405
        )

    try:
        data = json.loads(request.body)

        title = data.get("title")
        subject = data.get("subject")
        student_level = data.get("student_level")
        objectives = data.get("objectives")
        teaching_style = data.get("teaching_style", "standard")

        if not all([title, subject, student_level, objectives]):
            return JsonResponse(
                {"status": "error", "message": "Missing required fields"},
                status=400
            )

        objectives_text = "\n".join(objectives) if isinstance(objectives, list) else objectives

        prompt = f"""
You are an expert curriculum designer and instructional planner.

You must write a professional lesson plan in clear, formal English only.

ABSOLUTE RULES (CRITICAL):
- Use ONLY English.
- Do NOT use Markdown, symbols, or formatting styles.
- Do NOT add any extra sections or titles beyond the required ones.
- Do NOT repeat any section.
- Do NOT add explanations outside the required structure.
- The output MUST strictly follow the required structure.

REQUIRED STRUCTURE (EXACT ORDER ONLY):

1. Introduction
2. Behavioral Objectives
3. Activities
4. Assessment
5. Adaptability Notes
6. Conclusion

IMPORTANT:
Start immediately with 'Introduction'.

----------------------------

1. Introduction:
Write a concise paragraph introducing the lesson topic, its importance, and relevance.

2. Behavioral Objectives:
Write measurable objectives. Each must end with (Easy / Medium / Hard).

3. Activities:
Create student worksheets only.

Format:
Sheet Title: ...
Difficulty Level: Easy / Medium / Hard

Instructions for Students:
Clear instructions.

Student Tasks:
2–4 questions only.
Each question ends with a question mark and blank lines:

Answer:
_____________________
_____________________
_____________________

No answers. No hints. No multiple choice.

After each worksheet:
Creative Ideas for the Teacher:
(one paragraph only)

4. Assessment:
Paragraph describing evaluation methods.

5. Adaptability Notes:
Paragraph describing adaptation for weak, average, advanced students.

6. Conclusion:
Short professional reflection.

STOP immediately after Conclusion.

Lesson Data:
Title: {title}
Subject: {subject}
Student Level: {student_level}
Objectives:
{objectives_text}
Teaching Style: {teaching_style}
"""

        result = process_lesson_logic(prompt=prompt)

        if result.get("status") == "success":
            analysis = result.get("analysis")

            return JsonResponse({
                "status": "ok",
                "message": "Lesson plan generated successfully",
                "data": analysis
            })

        return JsonResponse({
            "status": "error",
            "message": f"AI Error: {result.get('message')}"
        }, status=502)

    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": str(e)},
            status=500
        )
 
COMMON_7_9 = [
    {
        "code": "LNG.07.4.2.XX.013",
        "desc": "Uses simple and complex grammatical structures effectively in writing"
    },
    {
        "code": "LNG.07.4.3.XX.012",
        "desc": "Writes extended texts on familiar and unfamiliar descriptive topics"
    },
    {
        "code": "LNG.07.4.3.XX.013",
        "desc": "Interprets and analyzes information from multiple sources"
    },
    {
        "code": "LNG.07.4.3.XX.014",
        "desc": "Produces well-structured texts with clear main ideas and supporting details"
    }
]


GRADE_STANDARDS = {
    "3": [
        {
            "code": "LNG.03.4.3.XX.004",
            "desc": "Plans ideas before writing"
        },
        {
            "code": "LNG.03.4.3.XX.003",
            "desc": "Writes short, simple compound sentences on familiar topics"
        },
        {
            "code": "LNG.03.4.2.XX.008",
            "desc": "Applies basic spelling rules in writing"
        },
        {
            "code": "LNG.03.4.2.XX.009",
            "desc": "Uses basic language structures in writing"
        },
        {
            "code": "LNG.03.4.2.XX.007",
            "desc": "Uses punctuation marks correctly in writing"
        },
        {
            "code": "LNG.03.4.2.XX.006",
            "desc": "Uses morphological awareness to form and write new words"
        }
    ],

    "6": [
        {
            "code": "LNG.05.4.2.XX.010",
            "desc": "Applies spelling rules accurately in writing"
        },
        {
            "code": "LNG.05.4.2.XX.011",
            "desc": "Uses a range of basic sentence structures in writing"
        },
        {
            "code": "LNG.05.4.3.XX.007",
            "desc": "Writes simple descriptive texts on familiar topics"
        },
        {
            "code": "LNG.05.4.3.XX.008",
            "desc": "Plans and develops ideas before writing"
        },
        {
            "code": "LNG.05.4.3.XX.009",
            "desc": "Writes structured paragraphs with a clear main idea and supporting details"
        }
    ],

    "7": COMMON_7_9,
    "8": COMMON_7_9,
    "9": COMMON_7_9
}

@csrf_exempt
def upload_image_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            first_name = data.get("first_name")
            last_name = data.get("last_name")
            class_name = data.get("class_name")
            subject_name = data.get("subject_name")
            image_url = data.get("image_url")
            lan = data.get("lan", "English")    
            custom_standards = data.get("standards", None)


            if not all([first_name,last_name, class_name, subject_name, image_url]):
                return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)            
            
            if lan.lower() == "arabic":
                language_instruction = "يجب كتابة جميع النتائج باللغة العربية."
            else:
                language_instruction = "All responses must be written in English."
            
            # 🔥 Extract class number safely
            class_raw = str(class_name).strip()
            match = re.search(r"\d+", class_raw)
            class_key = match.group() if match else None

            if custom_standards is not None:
                standards = custom_standards
            else:
                standards = GRADE_STANDARDS.get(class_key, [])

            # Convert standards to text
            if not standards:
                standards_text = "- No predefined standards for this class"
            else:
                standards_text = "\n".join(
                    f"- {s['code']}: {s['desc']}"
                    for s in standards
                )

            prompt = f"""
{language_instruction}

You are an expert {subject_name} teacher analyzing a student's handwritten assignment.

Primary task: Identify mistakes in the student's work and return a JSON ONLY response.
You MUST use ONLY the following learning standards for evaluation:

{standards_text}

IMPORTANT RULES:
- You MUST choose the closest matching "linked_standard" from the provided list
- If there is no perfect match, select the MOST SIMILAR standard based on meaning
- Do NOT invent or modify LNG codes
- Every mistake MUST be linked to one standard (never leave it empty)
- Prioritize semantic meaning over exact wording match

JSON FORMAT:
{{
  "score": number (0-100),
  "strengths": ["Key strengths observed in the student's work"],
  "mistakes": [
    {{
      "text": "exact incorrect equation, sentence, or segment written by the student",
      "type": "content | language | structure | accuracy",
      "explanation": "brief explanation why this is incorrect"
    }}
  ],
  "notes": {{
    "rubric": {{
      "presentation": "Outstanding | Very Good | Good | Acceptable | Weak",
      "frequency_and_consistency": "Outstanding | Very Good | Good | Acceptable | Weak",
      "student_response_to_feedback": "Outstanding | Very Good | Good | Acceptable | Weak",
      "attainment_vs_curriculum": "Outstanding | Very Good | Good | Acceptable | Weak"
    }},
    "originality_percentage": number (0-100),
    "linked_standard": "Choose the correct LNG code based on rules below",
    "improvement_goal": "One actionable learning goal for the student",
    "pedagogical_feedback": "Feedback describing student's understanding and areas needing improvement"
  }}
}}

IMPORTANT:
- "mistakes" must always be an ARRAY; if none, return "mistakes": []
- Only quote text written by student in "text"; do not invent
- Never return codes like "MATH" or "CCSS"

Return JSON ONLY.
"""
            

# IMPORTANT:
# - "mistakes" must always be an ARRAY; if none, return "mistakes": []
# - Only quote text written by student in "text"; do not invent
# - Apply mandatory standards based on grade:
#   Grade 3: [LNG.03.4.3.XX.004, LNG.03.4.3.XX.003, LNG.03.4.2.XX.008]
#   Grade 6: [LNG.05.4.3.XX.009, LNG.05.4.3.XX.008, LNG.05.4.2.XX.010]
#   Grade 7/8/9: [LNG.07.4.3.XX.014, LNG.07.4.3.XX.013, LNG.07.4.3.XX.012]
#   Other: LNG.GENERIC
# - For Math/Science: Map problem solving to LNG.07.4.3.XX.014 or LNG.05.4.2.XX.010
# - Never return codes like "MATH" or "CCSS"

# Return JSON ONLY.
#             prompt = f"""
#             {language_instruction}

# You are an expert {subject_name} teacher analyzing a student's assignment from an image.

# Student: {first_name} {last_name}
# Grade/Class: {class_name}
# Subject: {subject_name}

# Carefully examine the student's handwritten work in the image.

# Your PRIMARY task is to detect and list mistakes in the student's work.

# Return the result strictly in VALID JSON format only.
# Do NOT include any text outside the JSON.

# JSON FORMAT:

# {{
#   "score": number (0-100),

#   "strengths": [
#     "List the key strengths observed in the student's work"
#   ],

#   "mistakes": [
#     {{
#       "text": "exact incorrect equation, sentence, or segment written by the student",
#       "type": "content | language | structure | accuracy",
#       "explanation": "short explanation of why this is incorrect"
#     }}
#   ],

#   "notes": {{
#     "rubric": {{
#       "presentation": "Outstanding | Very Good | Good | Acceptable | Weak",
#       "frequency_and_consistency": "Outstanding | Very Good | Good | Acceptable | Weak",
#       "student_response_to_feedback": "Outstanding | Very Good | Good | Acceptable | Weak",
#       "attainment_vs_curriculum": "Outstanding | Very Good | Good | Acceptable | Weak"
#     }},
#     "originality_percentage": number (0-100),
#     "linked_standard": "MANDATORY: Choose the correct LNG code based on the rules below",
#     "improvement_goal": "One clear actionable learning goal for the student",
#     "pedagogical_feedback": "Detailed feedback describing the student's understanding and areas needing improvement"
#   }}
# }}

            result = process_image_logic(image_url=image_url, prompt=prompt)
            
            if result.get("status") == "success":
                analysis = result.get("analysis")
                mistakes = result.get("mistakes", [])
                #notes = analysis.notes

                data = {
                    "score": analysis.get("score"),                 # هنا
                    "strengths": analysis.get("strengths", []), 
                    "mistakes": mistakes,
                    "notes": analysis.get("notes", {})  # dict,
                }

                return JsonResponse({
                    "status": "ok",
                    "message": "Analysis completed successfully",
                    "data": data
                })

            else:
                return JsonResponse({
                    "status": "error", 
                    "message": f"Gemini Error: {result.get('message')}"
                }, status=502)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)



@csrf_exempt
def evaluate_teacher_comment(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        image_url = data.get("image_url")
        teacher_comment = data.get("teacher_comment")


        if not all([image_url, teacher_comment]):
            return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)
        
        prompt = f"""
The student assignment image includes teacher feedback written in RED ink.

IMPORTANT INSTRUCTIONS:
- All RED text in the image represents teacher sub-comments.
- You MUST extract all red annotations from the image.
- Ignore student writing (usually in black or blue).
- If text overlaps, prioritize RED text as teacher feedback.
- If no red text is clearly visible, return an empty sub_comment_analysis array.
- Do not hallucinate or invent any sub-comments.

---

Teacher overall comment:
"{teacher_comment}"

---

Your tasks:

1. Carefully read the image.
2. Extract ALL teacher sub-comments written in RED.Only consider RED text that is clearly a teacher comment (a phrase or sentence), not single letters, symbols, or minor corrections.
3. Treat each red annotation as a separate sub-comment.
4. Evaluate whether the teacher's overall comment is consistent with the sub-comments.
5. If there is inconsistency, explain it.
6. Evaluate each sub-comment individually.

---

Return strictly valid JSON in the following format:

{{
"attainment": {{
"level": "Above | In line | Below | Weak",
"description": "..."
}},

"progress": {{
"level": "Better than expected | Expected | Limited | Weak",
"description": "..."
}},

"teacher_feedback_evaluation": {{
"clarity": "Excellent | Good | Average | Poor",
"constructiveness": "Excellent | Good | Average | Poor"
}},

"sub_comment_analysis": [
{{
"id": number,
"extracted_text": "the red comment exactly as seen",
"accuracy": number (0-100),
"clarity": "Excellent | Good | Average | Poor",
"helpfulness": "High | Medium | Low",
"problem": "..."
}}
],

"inconsistency_between_overall_and_subcomments": "Explain clearly",

"mistakes_in_feedback": [
{{
"text": "incorrect or weak feedback",
"explanation": "why it is a problem"
}}
],

"recommendations": "One actionable improvement"
}}

Return JSON only.
"""

        result = process_comment_logic(image_url=image_url, teacher_comment=teacher_comment, prompt=prompt)

        if result.get("status") == "success":
            analysis = result.get("analysis")
            sub_comment_analysis = analysis.get("sub_comment_analysis", [])

            filtered_sub_comments = [
                c for c in sub_comment_analysis
                if len(c["extracted_text"].split()) > 2  
            ]

            analysis["sub_comment_analysis"] = filtered_sub_comments
            return JsonResponse({
                "status": "ok",
                "message": "Analysis completed successfully",
                "data": analysis
            })
        else:
            return JsonResponse({
                "status": "error",
                "message": f"AI Error: {result.get('message')}"
            }, status=502)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def analyze_teacher_yearly_performance(request):
    
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        yearly_summary = data.get("yearly_summary", [])

        if not yearly_summary:
            return JsonResponse({"status": "error", "message": "Missing yearly_summary field"}, status=400)

        selected_evals = yearly_summary[-35:]
        filtered_evals = []
        all_mistakes_texts = []

        for eval_item in selected_evals:
            eval_data = eval_item.get("data", {})  
            mistakes = [
                {"text": m.get("text", ""), "explanation": m.get("explanation", "")}
                for m in eval_data.get("mistakes_in_feedback", [])
            ]

            for m in mistakes:
                all_mistakes_texts.append(m["text"])

            filtered_evals.append({
                "teacher_feedback_evaluation": eval_data.get("teacher_feedback_evaluation", {}),
                
                "mistakes_in_feedback": mistakes,
                "attainment": eval_data.get("attainment", {}),  
                "progress": eval_data.get("progress", {}),      
                "feedback_frequency": eval_data.get("feedback_frequency", {"total_comments": 1}), # جديد
                "date": eval_item.get("date") or datetime.now().strftime("%Y-%m-%d")
            })
        counter = Counter(all_mistakes_texts)
        recurring_issues = [{"text": text, "occurrences": count} for text, count in counter.items() if count > 1]
        prompt = f"""
You are a senior school inspector. Your task is to provide a DEFINITIVE professional evaluation of a teacher’s yearly performance.

# DATA INPUT
{json.dumps(yearly_summary, ensure_ascii=False, indent=2)}

# EVALUATION MANDATE (CRITICAL)
- You MUST assign a specific rating for every criterion. 
- "Not enough evidence" is NOT an acceptable response.
- If data is sparse or incomplete, use your professional judgment to extrapolate the most likely rating based on the overall trajectory, tone, and patterns found in the available entries.
- Always provide the "closest appropriate" rating from the scales below.

# 1) RATING SCALES
Assign exactly ONE value from these specific options:

- frequency_consistency & teacher_feedback:
  [Outstanding, Very good, Good, Acceptable, Weak]

- attainment:
  [Above, In line, Below, Weak]

- progress:
  [Better than expected, Expected, Limited, Weak]

# 2) ANALYTICAL INSIGHTS
- Overall evaluation: Judge "Clarity" and "Constructiveness" based on the linguistic style of the feedback provided.
- Recurring issues: Identify patterns even if they appear only twice. Count occurrences accurately.
- Trends over time: Compare early vs. late data points to determine if the performance is Improving, Declining, or Stable.

# 3) RECOMMENDATION
- Provide ONE actionable, high-impact recommendation that addresses the most prominent pattern in the data.

# OUTPUT FORMAT (STRICT JSON ONLY)
{{
  "ratings": {{
    "frequency_consistency": "Selected Value",
    "teacher_feedback": "Selected Value",
    "attainment": "Selected Value",
    "progress": "Selected Value"
  }},
  "analysis": {{
    "overall_evaluation": {{
      "clarity": "Excellent | Good | Average | Poor",
      "constructiveness": "Excellent | Good | Average | Poor"
    }},
    "recurring_issues": [
      {{
        "text": "Description of issue",
        "occurrences": 0
      }}
    ],
    "trends": "Final summary of performance trajectory"
  }},
  "recommendations": "One clear actionable recommendation"
}}

# FINAL CONSTRAINTS
- Return ONLY JSON.
- Ensure all fields are filled. 
- Use inference logic: If there is even one positive signal, map it to the closest positive rating. If no data exists for a specific field, mirror the rating of the most closely related category.
"""
#         prompt = f"""
# You are a senior school inspector analyzing a teacher’s performance based on feedback evaluations.

# The following data represents evaluations of the teacher across the year:

# {json.dumps(yearly_summary, ensure_ascii=False, indent=2)}

# --------------------------------------
# 1) OFFICIAL RATINGS (VERY IMPORTANT)
# --------------------------------------
# Evaluate the teacher ONLY based on the available evidence using the following criteria:

# - Frequency and consistency of marking and feedback
# - Feedback given by teacher
# - Attainment (inferred from the quality and impact of feedback)
# - Progress (based on improvement over time)

# Use ONLY the following rating scales:

# For frequency_consistency and teacher_feedback:
# Outstanding | Very good | Good | Acceptable | Weak

# For attainment:
# Above | In line | Below | Weak

# For progress:
# Better than expected | Expected | Limited | Weak

# IMPORTANT:
# - Base your ratings strictly on the provided data.
# - Do NOT guess or assume missing information.
# - Do NOT return "Not enough evidence"; always choose the closest matching rating from the scales above, even if the data is limited.

# --------------------------------------
# 2) ANALYTICAL INSIGHTS
# --------------------------------------
# Also provide:

# - Overall evaluation of feedback:
#   - Clarity
#   - Constructiveness

# - Recurring issues:
#   Identify repeated problems in feedback and include how many times they occur.

# - Trends over time:
#   Analyze changes from early evaluations to recent ones.
#   Clearly state if performance improved, declined, or remained stable.

# --------------------------------------
# 3) RECOMMENDATION
# --------------------------------------
# Provide ONE clear and actionable recommendation to improve the teacher’s feedback.

# --------------------------------------
# OUTPUT FORMAT (STRICT JSON ONLY)
# --------------------------------------

# {{
#   "ratings": {{
#     "frequency_consistency": "Outstanding | Very good | Good | Acceptable | Weak",
#     "teacher_feedback": "Outstanding | Very good | Good | Acceptable | Weak",
#     "attainment": "Above | In line | Below | Weak",
#     "progress": "Better than expected | Expected | Limited | Weak"
#   }},
#   "analysis": {{
#     "overall_evaluation": {{
#       "clarity": "Excellent | Good | Average | Poor",
#       "constructiveness": "Excellent | Good | Average | Poor"
#     }},
#     "recurring_issues": [
#       {{
#         "text": "...",
#         "occurrences": 0
#       }}
#     ],
#     "trends": "Summary of improvements, declines, or stability over the year"
#   }},
#   "recommendations": "One clear actionable recommendation"
# }}

# Return JSON only.
# Ensure all fields are present.
# Do not omit any field.
# """

        result = process_yearly_summary_logic(filtered_evals, prompt=prompt)

        if result.get("status") == "success":
            analysis = result.get("analysis")
            return JsonResponse({
                "status": "ok",
                "message": "Yearly analysis completed successfully",
                "data": analysis
            })
        else:
            return JsonResponse({
                "status": "error",
                "message": f"AI Error: {result.get('message')}"
            }, status=502)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def analyze_all_teachers(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        teachers = data.get("teachers", [])

        if not teachers:
            return JsonResponse({"status": "error", "message": "No teachers data provided"}, status=400)

        rating_map = {
            "Outstanding": 5,
            "Very good": 4,
            "Good": 3,
            "Acceptable": 2,
            "Weak": 1,
            "Above": 4,
            "In line": 3,
            "Below": 2,
            "Better than expected": 4,
            "Expected": 3,
            "Limited": 2
        }

        processed_teachers = []

        for t in teachers:
            name = t.get("name")
            analysis = t.get("analysis", {})

            ratings = analysis.get("ratings", {})

            scores = []
            for key in ["frequency_consistency", "teacher_feedback", "attainment", "progress"]:
                value = ratings.get(key)
                if value in rating_map:
                    scores.append(rating_map[value])

            overall_score = round(sum(scores) / len(scores), 2) if scores else 0

            issues = analysis.get("analysis", {}).get("recurring_issues", [])
            top_issue = max(issues, key=lambda x: x.get("occurrences", 0), default=None)

            trend_text = analysis.get("analysis", {}).get("trends", "").lower()

            if "improv" in trend_text:
                trend = "Improving"
            elif "declin" in trend_text:
                trend = "Declining"
            else:
                trend = "Stable"

            processed_teachers.append({
                "name": name,
                "score": overall_score,
                "trend": trend,
                "top_issue": top_issue
            })

        ranked_teachers = sorted(processed_teachers, key=lambda x: x["score"], reverse=True)
        prompt = f"""
# ROLE
You are a Senior Educational Auditor and Data Analyst. Your task is to rank and analyze teacher performance data to assist school leadership.

# INPUT DATA
{json.dumps(ranked_teachers, ensure_ascii=False, indent=2)}

# SYSTEM LOGIC
1. **Ranking Metric**: Rank teachers based on a weighted average of their performance scores, feedback consistency, and progress trends.
2. **Segmentation**: Categorize teachers into 'Top Performers' (Top 20%), 'Steady' (Middle 60%), and 'Underperformers' (Bottom 20%).
3. **Commonality Analysis**: Identify issues that appear in more than 30% of the teacher profiles.

# OUTPUT FORMAT (STRICT JSON ONLY)
{{
  "ranking": [
    {{
      "rank": 1,
      "teacher_name": "Name",
      "performance_tier": "Top Performer",
      "primary_strength": "Short description"
    }}
  ],
  "executive_summary": {{
    "top_performers_count": 0,
    "underperformers_count": 0,
    "common_issues": [
      {{ "issue": "String", "frequency": "0%" }}
    ],
    "critical_insight": "A data-driven observation about the overall staff performance",
    "strategic_recommendation": "One high-level action for the school principal"
  }}
}}

# CONSTRAINTS
- Return ONLY JSON.
- Be objective and data-driven.
- Do not invent names or data not present in the input.
"""
#         prompt = f"""
# You are an expert educational evaluator.

# Here is processed data for teachers:

# {json.dumps(ranked_teachers, ensure_ascii=False, indent=2)}

# TASK:
# 1. Rank teachers from best to worst.
# 2. Identify top performers and weak performers.
# 3. Identify most common issues.
# 4. Provide insight.
# 5. Provide one recommendation.

# RETURN JSON ONLY.
# """

        client = GeminiClient(api_key=GEMINI_API_KEY)
        ai_response = client.analyze_json(ranked_teachers, prompt=prompt)
        return JsonResponse({
            "status": "ok",
            "ai_analysis": ai_response
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def check_corrected_mistakes_view(request):
    
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        image_url = data.get("image_url")
        mistakes = data.get("mistakes", [])
        lan = data.get("lan", "English")

        if not image_url or not isinstance(mistakes, list):
            return JsonResponse({"status": "error", "message": "Missing image_url or mistakes"}, status=400)

        if lan.lower() == "arabic":
            language_instruction = "يجب كتابة جميع النتائج باللغة العربية."
        else:
            language_instruction = "All responses must be written in English."

        prompt = f"""
        {language_instruction}

You are an expert teacher. A student has resubmitted an assignment image after receiving feedback. 
Your task is to check if the student corrected the previous mistakes.

Image URL: {image_url}

Previous mistakes to check:

{json.dumps(mistakes, ensure_ascii=False, indent=2)}

TASK:
- For each mistake, check if it has been corrected in the new image.
- Return two arrays:
  1) corrected_mistakes: mistakes that the student fixed
  2) uncorrected_mistakes: mistakes that still exist
- Do NOT invent new mistakes.
- Return ONLY JSON in the following format:

{{
  "corrected_mistakes": [
    {{"text": "...", "type": "...", "explanation": "..."}}
  ],
  "uncorrected_mistakes": [
    {{"text": "...", "type": "...", "explanation": "..."}}
  ],
  "recommendation": "One short actionable recommendation for the student"
}}
"""
        
        result = process_image_for_corrections(img_url=image_url, prompt=prompt)

        if result.get("status") != "success":
            return JsonResponse({"status": "error", "message": f"AI Error: {result.get('message')}"}, status=502)

        ai_data = result.get("analysis")

        return JsonResponse({
            "status": "ok",
            "message": "Checked corrected mistakes successfully",
            "data": ai_data
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

