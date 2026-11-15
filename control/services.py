from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from .models import Appointment, ScheduleTime

WEEKDAY_LABELS = [
    'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira',
    'Sexta-feira', 'Sábado', 'Domingo',
]


def generate_slots(start_time, end_time, interval_minutes):
    """
    Calcula os horários disponíveis de uma grade.

    Exemplo: uma grade de 08:00 a 12:00 com intervalo de 30 minutos
    gera 08:00, 08:30, 09:00... até 11:30. Só entram horários cujo
    atendimento termina dentro do fim da grade.
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
    Devolve os horários possíveis de um profissional em uma data.

    Junta os slots das grades fixa e semanal recorrente via
    generate_slots e remove os ocupados ('agendado') e os já
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


def available_slots_by_day(professional, start_date=None, days=21, exclude_appointment_id=None):
    """
    Agrupa os horários livres do profissional por dia.

    Retorna uma lista de dicionários com data, rótulo do dia da semana e
    a lista de horários disponíveis. Dias sem vaga são omitidos.
    """
    if start_date is None:
        start_date = timezone.localdate()
    result = []
    for offset in range(days):
        target_date = start_date + timedelta(days=offset)
        slots = available_slots(
            professional, target_date,
            exclude_appointment_id=exclude_appointment_id,
        )
        if slots:
            result.append({
                'date': target_date,
                'weekday_label': WEEKDAY_LABELS[target_date.weekday()],
                'slots': slots,
            })
    return result