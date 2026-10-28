from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render , get_object_or_404
from django.urls import reverse
from django.utils import timezone
from .models import Appointment

from datetime import datetime

from .services import available_slots , resolve_end_time
from .decorators import group_required
from .forms import SignupForm


def home_for(user):
    if user.is_staff or user.is_superuser:
        return '/admin/'
    groups = set(user.groups.values_list('name', flat=True))
    if 'central' in groups:
        return reverse('control:home')
    if 'profissional' in groups:
        return reverse('control:professional_home')
    if 'recepcao' in groups:
        return reverse('control:recepcao_home')
    return reverse('control:pending')


def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('control:pending')
    else:
        form = SignupForm()
    return render(request, 'control/signup.html', {'form': form})


def login_view(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(home_for(user))
        from django.contrib.auth.models import User
        try:
            candidate = User.objects.get(username=username)
            if candidate.check_password(password) and not candidate.is_active:
                return redirect('control:pending')
        except User.DoesNotExist:
            pass
        error = 'Usuário ou senha inválidos.'
    return render(request, 'control/login.html', {'error': error})


def pending_view(request):
    return render(request, 'control/pending.html')


@login_required
def home_view(request):
    return render(request, 'control/home.html', {
        'groups': list(request.user.groups.values_list('name', flat=True)),
    })


def logout_view(request):
    logout(request)
    return redirect('control:login')


@group_required('recepcao')
def recepcao_home(request):
    """
    permitido so a visualiação dos dados 
    """
    today = timezone.localdate()
    upcoming = Appointment.objects.filter(status='agendado', date__gte=today).order_by('date', 'start_time')
    overdue_list = Appointment.objects.filter(status='agendado', date__lt=today).order_by('date', 'start_time')
    history = Appointment.objects.exclude(status='agendado').order_by('-date', '-start_time')[:100]
    return render(request, 'control/recepcao_home.html', {
        'upcoming': upcoming, 'overdue_list': overdue_list, 'history': history,
    })
    
    
# Area views central 
@group_required('central')
def central_home(request):
    professionals = User.objects.filter(groups__name='profissional')
    slots, selected_pro, selected_date = [], None, ''
    pro_id = request.GET.get('professional', '')
    selected_date = request.GET.get('date', '')
    if pro_id and selected_date:
        selected_pro = get_object_or_404(User, pk=pro_id, groups__name='profissional')
        target = datetime.strptime(selected_date, '%Y-%m-%d').date()
        slots = available_slots(selected_pro, target)
        upcoming = Appointment.objects.filter(professional=selected_pro, status='agendado').order_by('date', 'start_time')
    else:
        upcoming = Appointment.objects.filter(status='agendado').order_by('date', 'start_time')
    return render(request, 'control/central_home.html', {
        'professionals': professionals, 'slots': slots,
        'selected_pro': selected_pro, 'selected_date': selected_date,
        'upcoming': upcoming,
    })

@group_required('central')
def appointment_create(request):
    if request.method != 'POST':
        return redirect('control:central_home')
    pro = get_object_or_404(User, pk=request.POST['professional'], groups__name='profissional')
    target = datetime.strptime(request.POST['date'], '%Y-%m-%d').date()
    start = datetime.strptime(request.POST['start_time'], '%H:%M').time()
    if start not in available_slots(pro, target):
        return render(request, redirect('control:central_home'), {'error': 'Horário indisponível.'})
    Appointment.objects.create(
        professional=pro, created_by=request.user,
        service_type=request.POST.get('service_type', ''),  # ver nota abaixo
        client=request.POST['client'].strip(), cpf=request.POST.get('cpf', ''),
        phone=request.POST.get('phone', ''), comments=request.POST.get('comments', ''),
        date=target, start_time=start, end_time=resolve_end_time(pro, target, start),
    )
    return redirect('control:central_home')

@group_required('central')
def appointment_edit(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        for field in ('client', 'cpf', 'phone', 'service_type', 'comments'):
            value = request.POST.get(field)
            if value is not None:
                setattr(appt, field, value.strip() if isinstance(value, str) else value)
        appt.save()
        return redirect('control:central_home')
    return render(request, 'control/appointment_form.html', {'appt': appt})

@group_required('central', 'profissional')
def appointment_reschedule(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if appt.professional != request.user and not request.user.groups.filter(name='central').exists() and not request.user.is_staff:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    error, slots, new_date = None, [], ''
    if request.method == 'POST':
        new_date = request.POST['date']
        target = datetime.strptime(new_date, '%Y-%m-%d').date()
        start = datetime.strptime(request.POST['start_time'], '%H:%M').time()
        if start not in available_slots(appt.professional, target, exclude_appointment_id=appt.pk):
            error = 'Horário indisponível.'
        else:
            appt.date, appt.start_time = target, start
            appt.end_time = resolve_end_time(appt.professional, target, start)
            appt.num_reschedules += 1
            appt.save()
            return redirect('control:central_home')
    return render(request, 'control/reschedule_form.html', {'appt': appt, 'error': error})