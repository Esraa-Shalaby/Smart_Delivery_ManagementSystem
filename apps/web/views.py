from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from .forms import LoginForm, RegisterForm


def dashboard_url(user):
    name = {"MANAGER": "manager:dashboard", "DRIVER": "driver:dashboard"}.get(
        user.role, "customer:dashboard"
    )
    return reverse(name)


class LoginView(auth_views.LoginView):
    template_name = "auth/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or dashboard_url(self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(0)
        return response


class RegisterView(FormView):
    template_name = "auth/register.html"
    form_class = RegisterForm

    def dispatch(self, request, *a, **kw):
        if request.user.is_authenticated:
            return redirect(dashboard_url(request.user))
        return super().dispatch(request, *a, **kw)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect(dashboard_url(user))


def logout_view(request):
    logout(request)
    return redirect("home")


class PasswordResetPage(TemplateView):
    template_name = "auth/forget_pass.html"

    def post(self, request):
        messages.info(request, "Password reset isn't connected yet.")
        return redirect("accounts:login")


class RolePage(LoginRequiredMixin, TemplateView):
    role = None

    def dispatch(self, request, *a, **kw):
        u = request.user
        if u.is_authenticated and self.role and u.role != self.role:
            return redirect(dashboard_url(u))
        return super().dispatch(request, *a, **kw)


class ByRolePage(LoginRequiredMixin, TemplateView):
    templates = {}

    def get_template_names(self):
        return [self.templates[self.request.user.role]]


def page(template, role=None):
    return RolePage.as_view(template_name=template, role=role)


@login_required
@require_POST
def action_stub(request, **kwargs):
    messages.info(request, "This action isn't wired to the backend yet.")
    return redirect(request.META.get("HTTP_REFERER") or "/")