from calendar import Calendar
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .decorators import group_required
from .forms import AppointmentForm, ScheduleTimeForm, SignupForm
from .models import Appointment, ScheduleTime
from .services import available_slots, available_slots_by_day, resolve_end_time

MONTH_NAMES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]
CALENDAR_WEEKDAYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']


def _parse_month(value, default):
    """Converte 'YYYY-MM' em uma data no primeiro dia do mês."""
    try:
        year, month = (int(part) for part in value.split('-', 1))
        return date(year, month, 1)
    except (AttributeError, TypeError, ValueError):
        return default


def _parse_date(value):
    """Converte 'YYYY-MM-DD' em date, devolvendo None quando inválido."""
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _shift_month(anchor, delta):
    month_index = anchor.month - 1 + delta
    year = anchor.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _central_url(professional=None):
    url = reverse('control:central_home')
    if professional is not None:
        return f'{url}?professional={professional.pk}'
    return url


def landing_view(request):
    return render(request, 'control/pages/landing.html')


def home_for(user):
    if user.is_staff or user.is_superuser:
        return reverse('admin:index')
    groups = set(user.groups.values_list('name', flat=True))
    if 'central' in groups:
        return reverse('control:central_home')
    if 'profissional' in groups:
        return reverse('control:professional_home')
    if 'recepcao' in groups:
        return reverse('control:recepcao_home')
    return reverse('control:pending')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('control:home')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cadastro recebido! Aguarde a aprovação do administrador.')
            return redirect('control:pending')
    else:
        form = SignupForm()
    return render(request, 'control/auth/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('control:home')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(home_for(user))
        try:
            candidate = User.objects.get(username=username)
            if candidate.check_password(password) and not candidate.is_active:
                return redirect('control:pending')
        except User.DoesNotExist:
            pass
        error = 'Usuário ou senha inválidos.'
    return render(request, 'control/auth/login.html', {'error': error})


def pending_view(request):
    return render(request, 'control/auth/pending.html')


def home_view(request):
    """
    Ponto de entrada do app: manda cada usuário para a página do seu perfil
    e mostra a landing page para visitantes não autenticados.
    """
    if request.user.is_authenticated:
        return redirect(home_for(request.user))
    return landing_view(request)


def logout_view(request):
    logout(request)
    return redirect('control:login')


@group_required('recepcao')
def recepcao_home(request):
    """
    Recepção: apenas agendados e histórico, sem atrasados nem observações.
    """
    today = timezone.localdate()
    upcoming = Appointment.objects.filter(
        status='agendado', date__gte=today
    ).select_related('professional').order_by('date', 'start_time')
    history_qs = Appointment.objects.exclude(
        status='agendado'
    ).select_related('professional').order_by('-date', '-start_time')
    return render(request, 'control/pages/recepcao_home.html', {
        'upcoming': upcoming,
        'history': history_qs[:50],
        'today_count': upcoming.filter(date=today).count(),
        'upcoming_count': upcoming.count(),
        'history_count': history_qs.count(),
    })


@login_required
def historico_view(request):
    # Histórico com filtros: cliente, cpf, telefone, período, status, profissional, atendente
    sql = Appointment.objects.exclude(status='agendado').select_related(
        'professional', 'created_by'
    )
    cliente = request.GET.get('cliente', '').strip()
    cpf = request.GET.get('cpf', '').strip()
    telefone = request.GET.get('telefone', '').strip()
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    status_f = request.GET.get('status', '')
    prof_id = request.GET.get('profissional', '')
    atendente = request.GET.get('atendente', '').strip()

    if cliente:
        sql = sql.filter(client__icontains=cliente)
    if cpf:
        sql = sql.filter(cpf__icontains=cpf)
    if telefone:
        sql = sql.filter(phone__icontains=telefone)
    start = _parse_date(data_inicio)
    end = _parse_date(data_fim)
    if start:
        sql = sql.filter(date__gte=start)
    if end:
        sql = sql.filter(date__lte=end)
    if status_f in dict(Appointment.STATUS):
        sql = sql.filter(status=status_f)
    if prof_id:
        try:
            sql = sql.filter(professional_id=int(prof_id))
        except ValueError:
            pass
    if atendente:
        sql = sql.filter(created_by__username__icontains=atendente)

    total = sql.count()
    sql = sql.order_by('-date', '-start_time')[:200]
    return render(request, 'control/pages/historico.html', {
        'agendamentos': sql,
        'filtros': request.GET,
        'is_recepcao': request.user.groups.filter(name='recepcao').exists(),
        'professionals': User.objects.filter(
            groups__name='profissional', is_active=True
        ).order_by('first_name', 'username'),
        'status_choices': Appointment.STATUS,
        'total': total,
    })


@group_required('profissional')
def professional_home(request):
    # Painel do profissional: hoje, atrasados, próximos, calendário e grade própria
    today = timezone.localdate()
    month_anchor = _parse_month(request.GET.get('month'), today.replace(day=1))
    selected_day = _parse_date(request.GET.get('day'))

    today_list = Appointment.objects.filter(
        professional=request.user, status='agendado', date=today
    ).select_related('created_by').order_by('start_time')
    overdue_list = Appointment.objects.filter(
        professional=request.user, status='agendado', date__lt=today
    ).select_related('created_by').order_by('date', 'start_time')
    upcoming = Appointment.objects.filter(
        professional=request.user, status='agendado', date__gt=today
    ).select_related('created_by').order_by('date', 'start_time')
    schedules = ScheduleTime.objects.filter(
        professional=request.user
    ).order_by('recurring', 'day_week', 'date', 'start_time')

    month_start = month_anchor
    month_end = _shift_month(month_anchor, 1) - timedelta(days=1)
    month_counts = {
        row['date']: row['total']
        for row in Appointment.objects.filter(
            professional=request.user, date__range=(month_start, month_end)
        ).values('date').annotate(total=Count('id'))
    }

    calendar_weeks = []
    for week in Calendar(firstweekday=0).monthdayscalendar(month_anchor.year, month_anchor.month):
        row = []
        for day_number in week:
            if day_number == 0:
                row.append(None)
                continue
            day_date = date(month_anchor.year, month_anchor.month, day_number)
            row.append({
                'date': day_date,
                'day': day_number,
                'count': month_counts.get(day_date, 0),
                'has_appointments': day_date in month_counts,
                'is_today': day_date == today,
                'is_selected': day_date == selected_day,
            })
        calendar_weeks.append(row)

    selected_day_appointments = []
    if selected_day:
        selected_day_appointments = Appointment.objects.filter(
            professional=request.user, date=selected_day
        ).select_related('created_by').order_by('start_time')

    prev_anchor = _shift_month(month_anchor, -1)
    next_anchor = _shift_month(month_anchor, 1)
    month_param = month_anchor.strftime('%Y-%m')
    return render(request, 'control/pages/professional_home.html', {
        'today': today,
        'today_list': today_list,
        'overdue_list': overdue_list,
        'upcoming': upcoming,
        'schedules': schedules,
        'today_count': today_list.count(),
        'overdue_count': overdue_list.count(),
        'upcoming_count': upcoming.count(),
        'schedule_count': schedules.count(),
        'calendar_weeks': calendar_weeks,
        'calendar_weekdays': CALENDAR_WEEKDAYS,
        'calendar_month_label': f'{MONTH_NAMES[month_anchor.month - 1]} {month_anchor.year}',
        'month_param': month_param,
        'prev_month': prev_anchor.strftime('%Y-%m'),
        'next_month': next_anchor.strftime('%Y-%m'),
        'selected_day': selected_day,
        'selected_day_appointments': selected_day_appointments,
    })


@group_required('profissional')
def schedule_create(request):
    # Criar nova grade (fixa ou semanal) para o profissional
    if request.method == 'POST':
        form = ScheduleTimeForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.professional = request.user
            obj.save()
            messages.success(request, 'Grade de horários cadastrada com sucesso.')
            return redirect('control:professional_home')
        messages.error(request, 'Revise os campos da grade antes de salvar.')
    else:
        form = ScheduleTimeForm(initial={
            'date': timezone.localdate() + timedelta(days=1),
            'interval': 30,
        })
    return render(request, 'control/schedules/schedule_form.html', {'form': form})


@group_required('profissional')
def schedule_delete(request, pk):
    # Excluir grade do próprio profissional
    obj = get_object_or_404(ScheduleTime, pk=pk, professional=request.user)
    obj.delete()
    messages.success(request, 'Grade de horários removida.')
    return redirect('control:professional_home')


@group_required('profissional')
def appointment_status(request, pk):
    # Apenas o profissional dono pode alterar o status do próprio agendamento
    appt = get_object_or_404(Appointment, pk=pk, professional=request.user)
    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        if new_status in dict(Appointment.STATUS):
            appt.status = new_status
            appt.save()
            messages.success(request, f'Status de {appt.client} atualizado para {appt.get_status_display()}.')
        else:
            messages.error(request, 'Status inválido.')
    return redirect('control:professional_home')


@group_required('central')
def central_home(request):
    professionals = User.objects.filter(
        groups__name='profissional', is_active=True
    ).distinct().order_by('first_name', 'username')
    selected_pro = None
    available_days = []
    selected_schedules = []
    pro_id = request.GET.get('professional', '')
    if pro_id:
        selected_pro = get_object_or_404(
            User, pk=pro_id, groups__name='profissional'
        )
        available_days = available_slots_by_day(
            selected_pro, timezone.localdate(), days=21
        )
        selected_schedules = ScheduleTime.objects.filter(
            professional=selected_pro
        ).order_by('recurring', 'day_week', 'date', 'start_time')

    today = timezone.localdate()
    upcoming = Appointment.objects.filter(
        status='agendado', date__gte=today
    ).select_related('professional').order_by('date', 'start_time')
    if selected_pro:
        upcoming = upcoming.filter(professional=selected_pro)

    return render(request, 'control/pages/central_home.html', {
        'professionals': professionals,
        'selected_pro': selected_pro,
        'selected_schedules': selected_schedules,
        'available_days': available_days,
        'upcoming': upcoming[:100],
        'upcoming_count': upcoming.count(),
        'booking_form': AppointmentForm(),
        'error': request.GET.get('error', ''),
    })


@group_required('central')
def appointment_create(request):
    if request.method != 'POST':
        return redirect('control:central_home')

    pro_id = request.POST.get('professional')
    try:
        pro = User.objects.get(pk=pro_id, groups__name='profissional')
    except (User.DoesNotExist, ValueError, TypeError):
        messages.error(request, 'Selecione um profissional válido.')
        return redirect('control:central_home')

    target = _parse_date(request.POST.get('date', ''))
    try:
        start = datetime.strptime(request.POST.get('start_time', ''), '%H:%M').time()
    except (TypeError, ValueError):
        start = None
    if target is None or start is None:
        messages.error(request, 'Data ou horário inválido.')
        return redirect(_central_url(pro))

    if start not in available_slots(pro, target):
        messages.error(request, 'Este horário não está mais disponível. Escolha outro.')
        return redirect(_central_url(pro))

    form = AppointmentForm(request.POST)
    if not form.is_valid():
        for field, errors in form.errors.items():
            label = form.fields[field].label if field in form.fields else ''
            for error in errors:
                messages.error(request, f'{label}: {error}' if label else error)
        return redirect(_central_url(pro))

    try:
        end = resolve_end_time(pro, target, start)
    except ValueError:
        messages.error(request, 'Horário fora da grade do profissional.')
        return redirect(_central_url(pro))

    appt = form.save(commit=False)
    appt.professional = pro
    appt.created_by = request.user
    appt.date = target
    appt.start_time = start
    appt.end_time = end
    appt.save()
    messages.success(
        request,
        f'Agendamento de {appt.client} criado para {target:%d/%m/%Y} às {start:%H:%M}.'
    )
    return redirect(_central_url(pro))


@group_required('central')
def appointment_edit(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    form = AppointmentForm(request.POST or None, instance=appt)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Agendamento de {appt.client} atualizado.')
        return redirect(_central_url(appt.professional))
    if request.method == 'POST':
        messages.error(request, 'Revise os dados do agendamento.')
    return render(request, 'control/appointments/appointment_form.html', {
        'appt': appt,
        'form': form,
    })


@group_required('central', 'profissional')
def appointment_reschedule(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    is_central_user = request.user.groups.filter(name='central').exists()
    if appt.professional != request.user and not is_central_user and not request.user.is_staff:
        raise PermissionDenied

    error = None
    if request.method == 'POST':
        target = _parse_date(request.POST.get('date', ''))
        try:
            start = datetime.strptime(request.POST.get('start_time', ''), '%H:%M').time()
        except (TypeError, ValueError):
            start = None
        if target is None or start is None:
            error = 'Data ou horário inválido.'
        elif start not in available_slots(
            appt.professional, target, exclude_appointment_id=appt.pk
        ):
            error = 'Horário indisponível. Escolha outro.'
        else:
            appt.date = target
            appt.start_time = start
            appt.end_time = resolve_end_time(appt.professional, target, start)
            appt.num_reschedules += 1
            appt.save()
            messages.success(
                request,
                f'Agendamento de {appt.client} remarcado para {target:%d/%m/%Y} às {start:%H:%M}.'
            )
            if is_central_user:
                return redirect(_central_url(appt.professional))
            return redirect('control:professional_home')
        messages.error(request, error)

    available_days = available_slots_by_day(
        appt.professional, timezone.localdate(), days=21,
        exclude_appointment_id=appt.pk,
    )
    return render(request, 'control/appointments/reschedule_form.html', {
        'appt': appt,
        'available_days': available_days,
        'error': error,
        'is_central_user': is_central_user,
    })


def error_403(request, exception):
    """Renderiza a página 403 para usuários sem permissão de acesso."""
    return render(request, 'control/errors/403.html', status=403)


def error_404(request, exception):
    """Renderiza a página 404 para rotas ou recursos inexistentes."""
    return render(request, 'control/errors/404.html', status=404)


def error_500(request):
    """Renderiza a página 500 sem expor detalhes técnicos ao usuário."""
    return render(request, 'control/errors/500.html', status=500)
