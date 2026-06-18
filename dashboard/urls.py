# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'  # <- هذا السطر يحل مشكلة الـ namespace

urlpatterns = [
    #path("", views.home, name="home"),

    # صفحة HTML للـ Dashboard
    path('upload-image/', views.upload_image_view, name='upload_image'),
    path('evaluate_teacher_comment/', views.evaluate_teacher_comment, name='evaluate_teacher_comment'),
    path('analyze_teacher_yearly_performance/', views.analyze_teacher_yearly_performance, name='analyze_teacher_yearly_performance'),
    path('check-corrected-mistakes/', views.check_corrected_mistakes_view, name='check_corrected_mistakes'),
    path('analyze-teachers/', views.analyze_all_teachers, name='analyze_teachers'),
    path('generate-lesson-plan/', views.generate_lesson_plan, name='generate_lesson_plan'),

    ]
