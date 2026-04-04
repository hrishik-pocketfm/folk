from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Students
    path('students/add/', views.add_student, name='add_student'),
    path('students/<int:pk>/', views.student_profile, name='student_profile'),
    path('students/<int:pk>/edit/', views.edit_student, name='edit_student'),
    path('students/<int:pk>/add-session/', views.add_session, name='add_session'),
    path('students/<int:pk>/delete/', views.delete_student, name='delete_student'),

    # Recommender
    path('recommender/', views.recommender, name='recommender'),
    path('recommender/call-status/', views.update_call_status, name='update_call_status'),
    path('regions/select/', views.set_current_region, name='set_current_region'),
    path('regions/create/', views.create_region, name='create_region'),

    # Admin
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_add, name='user_add'),

    # FOLK section
    path('folk/', views.folk_home, name='folk_home'),
    path('folk/sessions/', views.folk_sessions_list, name='folk_sessions_list'),
    path('folk/sessions/new/', views.folk_session_new, name='folk_session_new'),
    path('folk/sessions/<int:pk>/', views.folk_session_detail, name='folk_session_detail'),
    path('folk/sessions/<int:pk>/delete/', views.folk_session_delete, name='folk_session_delete'),
    path('folk/followup/', views.folk_followup_list, name='folk_followup_list'),
    path('folk/colleges/', views.colleges_list, name='colleges_list'),
    path('folk/colleges/<int:pk>/', views.college_detail, name='college_detail'),
    path('folk/colleges/<int:pk>/delete/', views.college_delete, name='college_delete'),
]
