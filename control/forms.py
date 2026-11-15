from django import forms
from django.contrib.auth.models import User

from .models import Appointment, Profile, ScheduleTime


class AppointmentForm(forms.ModelForm):
    """Dados do cliente usados na criação e edição de agendamentos."""

    class Meta:
        model = Appointment
        fields = ['client', 'cpf', 'phone', 'service_type', 'comments']
        labels = {
            'client': 'Cliente',
            'cpf': 'CPF',
            'phone': 'Telefone',
            'service_type': 'Tipo de serviço',
            'comments': 'Observações',
        }
        widgets = {
            'client': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo do cliente',
                'autocomplete': 'off',
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '000.000.000-00',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'tel',
                'placeholder': '(11) 99999-9999',
            }),
            'service_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex.: consulta, exame, apoio',
            }),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações sobre o atendimento (opcional)',
            }),
        }


class ScheduleTimeForm(forms.ModelForm):
    # Formulario para criar grade de horario do profissional
    INTERVAL_CHOICES = [
        (15, '15 minutos'),
        (20, '20 minutos'),
        (30, '30 minutos'),
        (45, '45 minutos'),
        (60, '1 hora'),
        (90, '1 hora e 30 minutos'),
    ]

    interval = forms.TypedChoiceField(
        label='Intervalo entre horários',
        choices=INTERVAL_CHOICES,
        coerce=int,
        initial=30,
        help_text='Cada intervalo vira um horário disponível para agendamento.',
    )

    class Meta:
        model = ScheduleTime
        fields = ['recurring', 'day_week', 'date', 'start_time', 'end_time', 'interval']
        labels = {
            'recurring': 'Repetir semanalmente',
            'day_week': 'Dia da semana',
            'date': 'Data específica',
            'start_time': 'Início',
            'end_time': 'Fim',
        }
        help_texts = {
            'recurring': 'Ative para criar uma grade que se repete toda semana.',
            'date': 'Use esta opção para atender apenas em um dia.',
        }
        widgets = {
            'recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'day_week': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'},
            ),
            'start_time': forms.TimeInput(
                format='%H:%M',
                attrs={'type': 'time', 'class': 'form-control'},
            ),
            'end_time': forms.TimeInput(
                format='%H:%M',
                attrs={'type': 'time', 'class': 'form-control'},
            ),
        }


class SignupForm(forms.Form):
    # Formas para cadastro de usuários
    first_name = forms.CharField(
        label='Nome',
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Como você gostaria de ser chamado',
            'autocomplete': 'name',
        }),
    )
    username = forms.CharField(
        label='Usuário',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Escolha um nome de usuário',
            'autocomplete': 'username',
        }),
    )
    password = forms.CharField(
        label='Senha',
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Crie uma senha',
            'autocomplete': 'new-password',
        }),
        help_text='Use pelo menos 8 caracteres.',
    )
    password2 = forms.CharField(
        label='Confirmar senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repita a senha',
            'autocomplete': 'new-password',
        }),
    )
    requested_type = forms.ChoiceField(
        label='Perfil de acesso',
        choices=Profile.TYPE,
        widget=forms.RadioSelect,
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Esse usuário já está em uso.')
        return username

    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError('As senhas não conferem.')
        return password2

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data.get('first_name', '').strip(),
            is_active=False,  # nasce bloqueado, admin libera
        )
        Profile.objects.create(
            user=user,
            requested_type=self.cleaned_data['requested_type'],
        )
        return user
