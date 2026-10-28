from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from .models import Appointment, ScheduleTime


def generate_slots(start_time, end_time, interval_minutes):
    """
    para calcular o intervalo de horarios disponiveis 
    deixa opções marcaveis de 30 min , sem acesso aos dados do banco
    
    exemplo : pega um intervalo de horario de 08:00~12:00 
    separa em janelas de 30 min , 08:00-08:30 , 09:00-09:30,...
    """
    slots = []
    today = timezone.localdate()
    current = datetime.combine(today, start_time)
    end = datetime.combine(today, end_time)
    step = timedelta(minutes=interval_minutes)
    while current + step <= end:
        slots.append(current.time())
        current += step
    return slots


def available_slots(professional, target_date, exclude_appointment_id=None):
    """
    Devolve os horarios possiveis do uruario(profissional) 
    
    Junta os slots das grades fixa e semanal recorrente via
    generate_slots e remove os ocupados ('Agendado') e os já
    passados. Passe exclude_appointment_id ao remarcar para que
    o agendamento movido não bloqueie a si mesmo.
    """
    entries = ScheduleTime.objects.filter(
        Q(date=target_date) | Q(recurring=True, day_week=target_date.weekday()),
        professional=professional,
    )
    day_slots = set()
    for entry in entries:
        day_slots.update(generate_slots(entry.start_time, entry.end_time, entry.interval))

    booked = Appointment.objects.filter(
        professional=professional, date=target_date, status='agendado',
    )
    if exclude_appointment_id:
        booked = booked.exclude(pk=exclude_appointment_id)
    busy = set(booked.values_list('start_time', flat=True))

    today = timezone.localdate()
    now = timezone.localtime().time()
    free = []
    for slot in sorted(day_slots):
        if target_date < today:
            continue
        if target_date == today and slot <= now:
            continue
        if slot not in busy:
            free.append(slot)
    return free


def resolve_end_time(professional, target_date, start_time):
    """Calcula a hora de fim somando o intervalo da grade vigente.

    Localiza a entrada da grade que cobre start_time e soma seu
    intervalo. Levanta ValueError se fora da grade.
    """
    entry = ScheduleTime.objects.filter(
        Q(date=target_date) | Q(recurring=True, day_week=target_date.weekday()),
        professional=professional,
        start_time__lte=start_time,
        end_time__gt=start_time,
    ).first()
    if entry is None:
        raise ValueError('Horário fora da grade do profissional.')
    end = datetime.combine(target_date, start_time) + timedelta(minutes=entry.interval)
    return end.time()