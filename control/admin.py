from django.contrib import admin
from django.contrib.auth.models import Group
from .models import Profile , ScheduleTime , Appointment

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'requested_type', 'status', 'created_at')
    list_filter = ('status', 'requested_type')
    search_fields = ('user__username',)
    actions = ('aprovar', 'rejeitar')

    @admin.action(description='Aprovar selecionados')
    def aprovar(self, request, queryset):
        for perfil in queryset.filter(status='pendente'):
            perfil.user.is_active = True
            perfil.user.save()
            grupo, _ = Group.objects.get_or_create(name=perfil.requested_type)
            perfil.user.groups.add(grupo)
            perfil.status = 'aprovado'
            perfil.save()

    @admin.action(description='Rejeitar selecionados')
    def rejeitar(self, request, queryset):
        queryset.filter(status='pendente').update(status='rejeitado')
    
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    # personalizando o que aparece no painel admin
    list_display = ('client', 'professional', 'date', 'start_time', 'status', 'num_reschedules')
    list_filter = ('status', 'date')
    search_fields = ('client', 'cpf', 'phone')



@admin.register(ScheduleTime)
class ScheduleTimeAdmin(admin.ModelAdmin):
    # mostrando os horarios
    list_display = ('professional', 'date', 'start_time', 'end_time', 'recurring')
