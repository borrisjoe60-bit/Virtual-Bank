from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    path('dashboard/', login_required(views.DashBoard.as_view()), name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('kyc/', views.kyc_view, name='kyc'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='users/password_change.html', success_url='/settings/'), name='password_change'),
]
