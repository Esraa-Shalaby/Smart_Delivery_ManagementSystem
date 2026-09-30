from decimal import Decimal

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)

from apps.accounts.models import User
from apps.complaints.models import Complaint
from apps.shipments.models import Shipment


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


class ShipmentForm(forms.Form):
    pickup_address = forms.CharField(max_length=500)
    delivery_address = forms.CharField(max_length=500)
    package_description = forms.CharField(max_length=500)
    package_weight = forms.DecimalField(
        min_value=Decimal("0.1"), max_digits=8, decimal_places=2
    )


class ComplaintForm(forms.Form):
    shipment = forms.ModelChoiceField(
        queryset=Shipment.objects.none(),
        required=False,
        empty_label="Not related to a specific shipment",
    )
    subject = forms.CharField(max_length=150)
    description = forms.CharField(widget=forms.Textarea)
    priority = forms.ChoiceField(
        choices=Complaint.Priority.choices,
        initial=Complaint.Priority.MEDIUM,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["shipment"].queryset = Shipment.objects.filter(customer=user)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self._old_email = (self.instance.email or "").lower()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        # التسجيل بيخلي username = email، فنحدّثهم مع بعض عشان الدخول يفضل شغال
        if (user.username or "").lower() == self._old_email:
            user.username = user.email
        if commit:
            user.save()
        return user


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-input"