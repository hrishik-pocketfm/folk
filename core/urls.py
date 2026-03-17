from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/<int:pk>/', views.student_profile, name='student_profile'),
    path('students/<int:pk>/edit/', views.edit_student, name='edit_student'),
    path('students/<int:pk>/add-session/', views.add_session, name='add_session'),
    path('students/<int:pk>/delete/', views.delete_student, name='delete_student'),
    path('recommender/', views.recommender, name='recommender'),
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_add, name='user_add'),
]
