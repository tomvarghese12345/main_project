from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("delete_faculty/<int:faculty_id>/", views.delete_faculty, name="delete_faculty"),
    path("delete_classroom/<int:classroom_id>/", views.delete_classroom, name="delete_classroom"),
    path("delete_subject/<int:course_id>/", views.delete_subject, name="delete_subject"),
    path("delete_timetable/", views.delete_timetable, name="delete_timetable"),
    path('delete_assignment/<int:assignment_id>/', views.delete_assignment, name='delete_assignment'),

   
]
