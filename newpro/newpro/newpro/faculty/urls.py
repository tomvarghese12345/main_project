from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.faculty_login, name='faculty_login'),
    path('dashboard/', views.faculty_dashboard, name='faculty_dashboard'),
    path('logout/', views.faculty_logout, name='faculty_logout'),

    path('course-diary/', views.course_diary, name='course_diary'),
    path('course-diary/pdf/', views.course_diary_pdf, name='course_diary_pdf'),

    path('<str:type>/<int:obj_id>/pdf/', views.download_pdf, name='download_pdf'),

    # Faculty leave application
    path('apply-leave/', views.apply_leave, name='apply_leave'),
    path('submit-leave/', views.submit_leave, name='submit_leave'),

    # Admin side leave management
    path('admin/leaves/', views.leave_applications_admin, name='leave_applications_admin'),
    path('admin/leaves/<int:pk>/', views.leave_application_detail_admin, name='leave_application_detail_admin'),
]

