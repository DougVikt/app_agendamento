from django.db import models
from django.utils import timezone


class AppointmentQuerySet(models.QuerySet):
    # consultas reutilizaveis: uma regra, um lugar

    def active(self):
        return self.filter(status='agendado')

    def upcoming(self, today=None):
        today = today or timezone.localdate()
        return self.active().filter(date__gte=today)

    def overdue(self, today=None):
        today = today or timezone.localdate()
        return self.active().filter(date__lt=today)

    def history(self):
        return self.exclude(status='agendado')

    def for_professional(self, user):
        return self.filter(professional=user)

    def with_people(self):
        return self.select_related('professional', 'created_by')


class AppointmentManager(models.Manager.from_queryset(AppointmentQuerySet)):
    pass