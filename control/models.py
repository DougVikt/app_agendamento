from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import F, Q
from .managers import AppointmentManager
from django.utils import timezone
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
    
  
class ScheduleTime(models.Model):
    # Modelo para as grades de horario do profissional

    WEEKDAYS = [
        (0, 'Segunda'), (1, 'Terça'), (2, 'Quarta'), (3, 'Quinta'),
        (4, 'Sexta'), (5, 'Sabado'), (6, 'Domingo'),
    ]

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
    day_week = models.PositiveSmallIntegerField(
        'dia da semana', choices=WEEKDAYS, null=True, blank=True)

    class Meta:
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'
        ordering = ['date', 'start_time']
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F('start_time')),
                name='schedule_end_after_start',
            ),
            models.CheckConstraint(
                condition=(
                    Q(recurring=True, date__isnull=True, day_week__isnull=False)
                    | Q(recurring=False, date__isnull=False)
                ),
                name='schedule_valid_recurrence',
            ),
        ]

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError('Hora final deve ser depois da inicial.')
        if self.interval <= 0:
            raise ValidationError('Intervalo deve ser maior que zero.')
        if self.recurring:
            if self.date is not None:
                raise ValidationError('Grade semanal nao deve ter data.')
            if self.day_week is None:
                raise ValidationError('Grade semanal exige o dia da semana.')
        elif self.date is None:
            raise ValidationError('Grade fixa exige uma data.')

    def __str__(self):
        if self.recurring:
            return f"{self.professional.username} - semanal dia {self.day_week} {self.start_time}/{self.end_time}"
        return f"{self.professional.username} - {self.date} {self.start_time}/{self.end_time}"

    @property
    def next_dates(self):
        # Proximas datas concretas para grade semanal (a partir de hoje)
        if not self.recurring or self.day_week is None:
            return []
        from django.utils import timezone
        today = timezone.localdate()
        dates = []
        for i in range(7):
            d = today + __import__('datetime').timedelta(days=i)
            if d.weekday() == self.day_week:
                dates.append(d.strftime('%d/%m'))
                if len(dates) >= 3:
                    break
        return dates
    
    
class Appointment(models.Model):
    # model para o agendamento dos profissionais
    STATUS = [
        ('agendado', 'Agendado'),
        ('atendido', 'Atendido'),
        ('ausente', 'Ausente'),
        ('cancelado', 'Cancelado'),
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
    status = models.CharField(max_length=20, choices=STATUS, default='agendado')
    num_reschedules = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AppointmentManager()

    class Meta:
        verbose_name = 'Agendamento'
        ordering = ['-date', '-start_time']
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F('start_time')),
                name='appointment_end_after_start',
            ),
            models.UniqueConstraint(
                fields=['professional', 'date', 'start_time'],
                condition=Q(status='agendado'),
                name='unique_active_slot',
            ),
        ]

    def __str__(self):
        return f'{self.client} · {self.date} {self.start_time}'

    @property
    def reschedule_badge(self):
        # calcula quantas vezes o agendamento foi remarcado
        if self.num_reschedules == 1:
            return 'Remarcado'
        if self.num_reschedules > 1:
            return f'Remarcado{self.num_reschedules}x'
        return None

    @property
    def status_badge_class(self):
        # classe Bootstrap correspondente ao status atual
        return {
            'agendado': 'primary',
            'atendido': 'success',
            'ausente': 'warning text-dark',
            'cancelado': 'secondary',
        }.get(self.status, 'secondary')

    @property
    def overdue(self):
        # função para definir os agendamentos atrasados 
        from django.utils import timezone
        return self.status == 'agendado' and self.date < timezone.localdate()