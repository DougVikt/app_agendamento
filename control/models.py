from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    
    # Model base para perfil de cada usuario
    TYPE = [
        ('recepcao','Recepção'),
        ('central', 'Central de Atendimento'),
        ('profissional' , 'Profissional'),
    ]
    STATUS = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]
    
    user = models.OneToOneField(User , on_delete=models.CASCADE ,related_name='profile')
    requested_type = models.CharField('tipo solicitado' , max_length=20 ,choices=TYPE)
    status = models.CharField('status', max_length=10, choices=STATUS, default='pendente')
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name = 'Perfil'
    

    def __str__(self):
        return f'{self.user.username}({self.get_requested_type_display()})'
    
    @property
    def approved_group(self):
        return self.requested_type if self.status == 'aprovado' else None
    
    
class ScheduleTime(models.Model):
    
    # model para os horarios do profissional
    professional = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='time_slots',
        limit_choices_to={"groups__name":"profissional"}
    )
    date= models.DateField("data", null=True, blank=True)
    start_time = models.TimeField("inicio")
    end_time = models.TimeField("fim")
    interval = models.PositiveIntegerField("intervalo(min)" ,default=30)
    recurring = models.BooleanField("semanal", default=False)
    day_week = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'
        ordering = ['date' ,'start_time']
        
    def __str__(self):
        if self.recurring :
            return f"{self.professional.username} - semanal dia {self.day_week} {self.start_time}/{self.end_time}"
        return f"{self.professional.username} - {self.date} {self.start_time}/{self.end_time}"
    
    
class Appointment(models.Model):
    # model para o agendamento dos profissionais
    STATUS = [
        ('Agendado', 'Agendado'),
        ('Atendido', 'Atendido'),
        ('Ausente', 'Ausente'),
        ('Cancelado', 'Cancelado'),
    ]
    
    professional = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='appointments',
        limit_choices_to={"groups__name":"profissional"}
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='created_appointments'
    )
    service_type = models.CharField(max_length=100)
    client = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    comments = models.TextField(blank=True, default='')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS, default='Agendado')
    num_reschedules = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Agendamento'
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f'{self.client} · {self.date} {self.start_time}'

    @property
    def rescheduled_customer(self):
        # faz o calculo para as vezes que um cliente vou remarcado
        if self.num_reschedules == 1:
            return 'Remarcado'
        if self.num_reschedules > 1:
            return f'Remarcado{self.num_reschedules}x'
        return None

    @property
    def overdue(self):
        # função para definir os agendamentos atrasados 
        from django.utils import timezone
        return self.status == 'Agendado' and self.date < timezone.localdate()