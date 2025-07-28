from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django import forms
from .models import Destinatario, Organizacion
from django.contrib.auth import authenticate
import json

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

class DestinatarioForm(forms.ModelForm):
    apellido = forms.CharField(max_length=100, required=True, label="Apellido")
    
    def __init__(self, *args, organizacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organizacion = organizacion
        # Aplicar estilo consistente a todos los campos
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

    class Meta:
        model = Destinatario
        fields = ['nombre', 'email']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'required': True,
                'placeholder': 'Tu nombre'
            }),
            'email': forms.EmailInput(attrs={
                'required': True,
                'placeholder': 'tu@email.com'
            })
        }
        labels = {
            'nombre': 'Nombre',
            'email': 'Correo electrónico'
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Destinatario.objects.filter(email=email).exists():
            raise forms.ValidationError("Ese destinatario ya está registrado.")
        if self.organizacion:
            dominio_autorizado = self.organizacion.dominio.lower().strip()
            if not email.endswith(f"@{dominio_autorizado}"):
                raise forms.ValidationError(
                    "Solo puedes agregar destinatarios que pertenezcan a tu organización"
                )
        return email

class RegistroEmpresaAdminForm(forms.Form):
    nombre = forms.CharField(label="Nombre", max_length=100)
    apellido = forms.CharField(label="Apellido", max_length=100)
    email = forms.EmailField(label="Email")
    nombre_empresa = forms.CharField(label="Nombre de la empresa", max_length=200)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicar estilo consistente a todos los campos
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Las contraseñas no coinciden.")
        if User.objects.filter(email=cleaned_data.get("email")).exists():
            self.add_error('email', "Ese email ya está registrado.")
        return cleaned_data

class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise forms.ValidationError("No existe un usuario con ese email.")
            user = authenticate(username=user.username, password=password)
            if user is None:
                raise forms.ValidationError("Email o contraseña incorrectos.")
            cleaned_data['user'] = user
        return cleaned_data

class RegistroPruebaForm(forms.Form):
    nombre = forms.CharField(label="Nombre", max_length=100)
    apellido = forms.CharField(label="Apellido", max_length=100)
    email = forms.EmailField(label="Email")
    telefono = forms.CharField(label="Teléfono", max_length=30)
    empresa = forms.CharField(label="Nombre de la empresa", max_length=200)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput, required=True)

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if not password1 or not password2:
            self.add_error('password1', "Debes ingresar y confirmar la contraseña.")
        elif password1 != password2:
            self.add_error('password2', "Las contraseñas no coinciden.")
        return cleaned_data


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['old_password'].label = 'Contraseña actual'
        self.fields['new_password1'].label = 'Nueva contraseña'
        self.fields['new_password2'].label = 'Confirmar nueva contraseña' 