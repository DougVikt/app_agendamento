from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone
from datetime import date, time, timedelta

from .models import Profile, ScheduleTime, Appointment
from .services import available_slots, available_slots_by_day, generate_slots, resolve_end_time


class UserAndProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='medico1', password='senha123', is_active=True
        )
        self.group, _ = Group.objects.get_or_create(name='profissional')
        self.user.groups.add(self.group)
        self.profile = Profile.objects.create(
            user=self.user, requested_type='profissional', status='aprovado'
        )

    def test_usuario_criado_com_grupo(self):
        self.assertTrue(self.user.groups.filter(name='profissional').exists())

    def test_perfil_vinculado_ao_usuario(self):
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.status, 'aprovado')

    def test_usuario_nao_ativo_nao_pode_logar(self):
        User.objects.create_user(
            username='bloqueado', password='senha123', is_active=False
        )
        self.client = Client()
        response = self.client.post(reverse('control:login'), {
            'username': 'bloqueado', 'password': 'senha123'
        })
        # Usuário inativo é redirecionado para página de pendente (302)
        self.assertEqual(response.status_code, 302)


class ScheduleTimeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='prof1', password='senha123', is_active=True
        )
        self.group, _ = Group.objects.get_or_create(name='profissional')
        self.user.groups.add(self.group)

    def test_criar_horario_fixo(self):
        h = ScheduleTime.objects.create(
            professional=self.user,
            date=date(2026, 11, 5),
            start_time=time(8, 0),
            end_time=time(12, 0),
            interval=30,
            recurring=False,
            day_week=None,
        )
        self.assertEqual(str(h.professional), 'prof1')
        self.assertFalse(h.recurring)

    def test_criar_horario_semanal(self):
        h = ScheduleTime.objects.create(
            professional=self.user,
            date=None,
            start_time=time(14, 0),
            end_time=time(17, 0),
            interval=60,
            recurring=True,
            day_week=2,
        )
        self.assertTrue(h.recurring)
        self.assertIsNone(h.date)

    def test_end_nao_pode_ser_antes_de_inicio(self):
        with self.assertRaises(Exception):
            ScheduleTime.objects.create(
                professional=self.user,
                date=date(2026, 11, 5),
                start_time=time(12, 0),
                end_time=time(8, 0),
                interval=30,
                recurring=False,
                day_week=None,
            )


class AppointmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='atendente1', password='senha123', is_active=True
        )
        self.group, _ = Group.objects.get_or_create(name='central')
        self.user.groups.add(self.group)

        self.prof = User.objects.create_user(
            username='prof1', password='senha123', is_active=True
        )
        self.group_prof, _ = Group.objects.get_or_create(name='profissional')
        self.prof.groups.add(self.group_prof)

    def test_criar_agendamento(self):
        a = Appointment.objects.create(
            professional=self.prof,
            created_by=self.user,
            service_type='Consulta',
            client='João Silva',
            cpf='123.456.789-00',
            phone='11999999999',
            comments='Primeira consulta',
            date=date(2026, 11, 10),
            start_time=time(8, 0),
            end_time=time(8, 30),
            status='agendado',
        )
        self.assertEqual(a.client, 'João Silva')
        self.assertEqual(a.created_by, self.user)
        self.assertEqual(a.status, 'agendado')

    def test_agendamento_nao_pode_ter_hora_final_antes_da_inicial(self):
        with self.assertRaises(Exception):
            Appointment.objects.create(
                professional=self.prof,
                created_by=self.user,
                service_type='Consulta',
                client='João',
                date=date(2026, 11, 10),
                start_time=time(10, 0),
                end_time=time(9, 0),
                status='agendado',
            )


class ServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='prof_slot', password='senha123', is_active=True
        )
        self.group, _ = Group.objects.get_or_create(name='profissional')
        self.user.groups.add(self.group)

    def test_generate_slots_basico(self):
        slots = generate_slots(time(8, 0), time(12, 0), 30)
        self.assertIn('08:00', [s.strftime('%H:%M') for s in slots])
        self.assertIn('11:30', [s.strftime('%H:%M') for s in slots])
        self.assertNotIn('12:00', [s.strftime('%H:%M') for s in slots])

    def test_available_slots_com_horario_ocupado(self):
        ScheduleTime.objects.create(
            professional=self.user,
            date=date(2026, 11, 10),
            start_time=time(8, 0),
            end_time=time(12, 0),
            interval=30,
            recurring=False,
            day_week=None,
        )
        Appointment.objects.create(
            professional=self.user,
            service_type='Consulta',
            client='Ocupado',
            date=date(2026, 11, 10),
            start_time=time(8, 0),
            end_time=time(8, 30),
            status='agendado',
        )
        slots = available_slots(self.user, date(2026, 11, 10))
        slot_strings = [s.strftime('%H:%M') for s in slots]
        self.assertNotIn('08:00', slot_strings)
        self.assertIn('08:30', slot_strings)

    def test_resolve_end_time(self):
        ScheduleTime.objects.create(
            professional=self.user,
            date=date(2026, 11, 10),
            start_time=time(8, 0),
            end_time=time(12, 0),
            interval=30,
            recurring=False,
            day_week=None,
        )
        end = resolve_end_time(self.user, date(2026, 11, 10), time(8, 0))
        self.assertEqual(end, time(8, 30))


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='senha123', is_active=True
        )
        self.group, _ = Group.objects.get_or_create(name='recepcao')
        self.user.groups.add(self.group)

    def test_login_view_carrega(self):
        response = self.client.get(reverse('control:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_sucesso_redireciona(self):
        response = self.client.post(reverse('control:login'), {
            'username': 'testuser', 'password': 'senha123'
        })
        self.assertEqual(response.status_code, 302)

    def test_cadastro_view_carrega(self):
        response = self.client.get(reverse('control:signup'))
        self.assertEqual(response.status_code, 200)

    def test_historico_view_sem_login_redireciona(self):
        response = self.client.get(reverse('control:historico'))
        self.assertEqual(response.status_code, 302)

    def test_pendente_view_carrega(self):
        response = self.client.get(reverse('control:pending'))
        self.assertEqual(response.status_code, 200)


class RoutingTests(TestCase):
    """Garante que a raiz do app direciona cada perfil para sua página oficial."""

    def setUp(self):
        self.client = Client()

        self.recepcao = User.objects.create(username='recepcao_route', is_active=True)
        self.recepcao.groups.add(Group.objects.get_or_create(name='recepcao')[0])

        self.central = User.objects.create(username='central_route', is_active=True)
        self.central.groups.add(Group.objects.get_or_create(name='central')[0])

        self.profissional = User.objects.create(username='prof_route', is_active=True)
        self.profissional.groups.add(Group.objects.get_or_create(name='profissional')[0])

    def test_raiz_anonima_mostra_landing(self):
        response = self.client.get(reverse('control:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'control/pages/landing.html')

    def test_raiz_logada_recepcao_redireciona_para_pagina_oficial(self):
        self.client.force_login(self.recepcao)
        response = self.client.get(reverse('control:home'))
        self.assertRedirects(response, reverse('control:recepcao_home'))

    def test_raiz_logada_central_redireciona_para_pagina_oficial(self):
        self.client.force_login(self.central)
        response = self.client.get(reverse('control:home'))
        self.assertRedirects(response, reverse('control:central_home'))

    def test_raiz_logada_profissional_redireciona_para_pagina_oficial(self):
        self.client.force_login(self.profissional)
        response = self.client.get(reverse('control:home'))
        self.assertRedirects(response, reverse('control:professional_home'))

    def test_login_redireciona_cada_perfil_para_sua_pagina(self):
        for user, target in (
            (self.recepcao, 'control:recepcao_home'),
            (self.central, 'control:central_home'),
            (self.profissional, 'control:professional_home'),
        ):
            self.client.logout()
            user.set_password('senha123')
            user.save()
            response = self.client.post(reverse('control:login'), {
                'username': user.username, 'password': 'senha123',
            })
            self.assertRedirects(response, reverse(target))

    def test_recepcao_nao_recebe_atrasados(self):
        Appointment.objects.create(
            professional=self.profissional,
            service_type='Consulta',
            client='Atrasado',
            date=date(2020, 1, 1),
            start_time=time(8, 0),
            end_time=time(8, 30),
            status='agendado',
        )
        self.client.force_login(self.recepcao)
        response = self.client.get(reverse('control:recepcao_home'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('overdue_list', response.context)
        self.assertNotContains(response, 'Atrasados')

    def test_central_nao_recebe_atrasados(self):
        Appointment.objects.create(
            professional=self.profissional,
            service_type='Consulta',
            client='Atrasado',
            date=date(2020, 1, 1),
            start_time=time(8, 0),
            end_time=time(8, 30),
            status='agendado',
        )
        self.client.force_login(self.central)
        response = self.client.get(reverse('control:central_home'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Atrasado')

    def test_historico_ordena_por_data(self):
        for day in (date(2026, 1, 10), date(2026, 1, 20)):
            Appointment.objects.create(
                professional=self.profissional,
                service_type='Consulta',
                client=f'Cliente {day}',
                date=day,
                start_time=time(9, 0),
                end_time=time(9, 30),
                status='atendido',
            )
        self.client.force_login(self.central)
        response = self.client.get(reverse('control:historico'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [a.date for a in response.context['agendamentos']],
            [date(2026, 1, 20), date(2026, 1, 10)],
        )


class AvailabilityByDayTests(TestCase):
    def setUp(self):
        self.professional = User.objects.create(username='prof_dias', is_active=True)
        self.professional.groups.add(Group.objects.get_or_create(name='profissional')[0])
        self.target = timezone.localdate() + timedelta(days=2)

    def test_intervalo_de_45_minutos_gera_horarios_de_45_em_45(self):
        ScheduleTime.objects.create(
            professional=self.professional,
            date=self.target,
            start_time=time(8, 0),
            end_time=time(10, 0),
            interval=45,
            recurring=False,
        )
        days = available_slots_by_day(self.professional, self.target, days=1)
        self.assertEqual(len(days), 1)
        self.assertEqual(
            days[0]['slots'],
            [time(8, 0), time(8, 45)],
        )

    def test_dias_sem_grade_sao_omitidos(self):
        days = available_slots_by_day(self.professional, self.target, days=3)
        self.assertEqual(days, [])


class CentralSchedulingTests(TestCase):
    def setUp(self):
        self.central = User.objects.create(username='central_horarios', is_active=True)
        self.central.groups.add(Group.objects.get_or_create(name='central')[0])
        self.professional = User.objects.create(username='prof_horarios', is_active=True)
        self.professional.groups.add(Group.objects.get_or_create(name='profissional')[0])
        self.target = timezone.localdate() + timedelta(days=1)
        self.schedule = ScheduleTime.objects.create(
            professional=self.professional,
            date=self.target,
            start_time=time(8, 0),
            end_time=time(10, 0),
            interval=30,
            recurring=False,
        )
        self.client.force_login(self.central)

    def test_central_exibe_horarios_do_profissional_por_intervalo(self):
        response = self.client.get(
            reverse('control:central_home'),
            {'professional': self.professional.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['available_days']), 1)
        self.assertEqual(
            response.context['available_days'][0]['slots'],
            [time(8, 0), time(8, 30), time(9, 0), time(9, 30)],
        )
        self.assertContains(response, '08:00')
        self.assertContains(response, '30 min')

    def test_central_cria_agendamento_com_horario_clicado(self):
        response = self.client.post(reverse('control:appointment_create'), {
            'professional': self.professional.pk,
            'date': self.target.strftime('%Y-%m-%d'),
            'start_time': '08:30',
            'client': 'Cliente Central',
            'cpf': '123.456.789-00',
            'phone': '11999999999',
            'service_type': 'Consulta',
            'comments': 'Criado pelo teste',
        })
        self.assertRedirects(
            response,
            f"{reverse('control:central_home')}?professional={self.professional.pk}",
        )
        appointment = Appointment.objects.get(client='Cliente Central')
        self.assertEqual(appointment.start_time, time(8, 30))
        self.assertEqual(appointment.end_time, time(9, 0))
        self.assertEqual(appointment.created_by, self.central)


class ProfessionalCalendarTests(TestCase):
    def setUp(self):
        self.professional = User.objects.create(username='prof_calendario', is_active=True)
        self.professional.groups.add(Group.objects.get_or_create(name='profissional')[0])
        self.target = timezone.localdate() + timedelta(days=15)
        self.appointment = Appointment.objects.create(
            professional=self.professional,
            service_type='Consulta',
            client='Cliente Calendário',
            date=self.target,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status='agendado',
        )
        self.client.force_login(self.professional)

    def test_calendario_navega_entre_meses(self):
        response = self.client.get(
            reverse('control:professional_home'),
            {'month': self.target.strftime('%Y-%m')},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['month_param'], self.target.strftime('%Y-%m'))
        self.assertNotEqual(response.context['prev_month'], response.context['month_param'])
        self.assertNotEqual(response.context['next_month'], response.context['month_param'])
        self.assertContains(response, self.target.strftime('%Y'))

    def test_dia_do_calendario_filtra_agenda(self):
        response = self.client.get(
            reverse('control:professional_home'),
            {
                'month': self.target.strftime('%Y-%m'),
                'day': self.target.strftime('%Y-%m-%d'),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_day'], self.target)
        self.assertEqual(
            list(response.context['selected_day_appointments']),
            [self.appointment],
        )
        self.assertContains(response, 'Cliente Calendário')


class SignupFormTests(TestCase):
    def test_senhas_diferentes_nao_criam_usuario(self):
        response = self.client.post(reverse('control:signup'), {
            'first_name': 'Novo',
            'username': 'novo_usuario',
            'password': 'senha123',
            'password2': 'outra123',
            'requested_type': 'central',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('password2', response.context['form'].errors)
        self.assertFalse(User.objects.filter(username='novo_usuario').exists())

    def test_cadastro_salva_nome_e_perfil_pendente(self):
        response = self.client.post(reverse('control:signup'), {
            'first_name': 'Maria',
            'username': 'maria_teste',
            'password': 'senha123',
            'password2': 'senha123',
            'requested_type': 'profissional',
        })
        self.assertRedirects(response, reverse('control:pending'))
        user = User.objects.get(username='maria_teste')
        self.assertEqual(user.first_name, 'Maria')
        self.assertFalse(user.is_active)
        self.assertEqual(user.profile.requested_type, 'profissional')


class RescheduleTests(TestCase):
    def setUp(self):
        self.central = User.objects.create(username='central_remarca', is_active=True)
        self.central.groups.add(Group.objects.get_or_create(name='central')[0])
        self.professional = User.objects.create(username='prof_remarca', is_active=True)
        self.professional.groups.add(Group.objects.get_or_create(name='profissional')[0])
        self.target = timezone.localdate() + timedelta(days=1)
        ScheduleTime.objects.create(
            professional=self.professional,
            date=self.target,
            start_time=time(8, 0),
            end_time=time(10, 0),
            interval=30,
            recurring=False,
        )
        self.appointment = Appointment.objects.create(
            professional=self.professional,
            service_type='Consulta',
            client='Cliente Remarcar',
            date=self.target,
            start_time=time(8, 0),
            end_time=time(8, 30),
            status='agendado',
        )
        self.client.force_login(self.central)

    def test_tela_de_remarcacao_mostra_horarios_disponiveis(self):
        response = self.client.get(
            reverse('control:appointment_reschedule', args=[self.appointment.pk])
        )
        self.assertEqual(response.status_code, 200)
        slots = response.context['available_days'][0]['slots']
        self.assertIn(time(8, 0), slots)
        self.assertIn(time(8, 30), slots)

    def test_remarcacao_atualiza_horario_e_contador(self):
        response = self.client.post(
            reverse('control:appointment_reschedule', args=[self.appointment.pk]),
            {'date': self.target.strftime('%Y-%m-%d'), 'start_time': '08:30'},
        )
        self.assertRedirects(
            response,
            f"{reverse('control:central_home')}?professional={self.professional.pk}",
        )
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.start_time, time(8, 30))
        self.assertEqual(self.appointment.end_time, time(9, 0))
        self.assertEqual(self.appointment.num_reschedules, 1)
