from django.urls import path

from . import views

app_name = 'control'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('cadastro/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('pendente/', views.pending_view, name='pending'),
    path('logout/', views.logout_view, name='logout'),
    path('recepcao/', views.recepcao_home, name='recepcao_home'),
    path('historico/', views.historico_view, name='historico'),
    path('profissional/', views.professional_home, name='professional_home'),
    path('agendar/<int:pk>/status/', views.appointment_status, name='appointment_status'),
    path('profissional/horario/novo/', views.schedule_create, name='schedule_create'),
    path('profissional/horario/<int:pk>/excluir/', views.schedule_delete, name='schedule_delete'),
    path('central/', views.central_home, name='central_home'),
    path('agendar/novo/', views.appointment_create, name='appointment_create'),
    path('agendar/<int:pk>/editar/', views.appointment_edit, name='appointment_edit'),
    path('agendar/<int:pk>/remarcar/', views.appointment_reschedule, name='appointment_reschedule'),
]