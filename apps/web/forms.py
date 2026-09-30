from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.accounts.models import User


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False)

    def clean(self):
        ident = self.cleaned_data.get("username")
        if ident and "@" in ident:  # تسجيل الدخول بالإيميل
            u = User.objects.filter(email__iexact=ident).first()
            if u:
                self.cleaned_data["username"] = u.get_username()
        return super().clean()


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    role = forms.ChoiceField(
        choices=[(User.Role.CUSTOMER, "Customer"), (User.Role.DRIVER, "Driver")]
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "role")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user