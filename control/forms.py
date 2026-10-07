from django import forms
from django.contrib.auth.models import User

from .models import Profile


class SignupForm(forms.Form):
    # formas para cadastro de usuarios
    username = forms.CharField(label='Usuário', max_length=150)
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)
    requested_type = forms.ChoiceField(label='Quero entrar como', choices=Profile.TYPE)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Esse usuário já está em uso.')
        return username

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            is_active=False,  # nasce bloqueado, admin libera
        )
        Profile.objects.create(user=user, requested_type=self.cleaned_data['requested_type'])
        return user