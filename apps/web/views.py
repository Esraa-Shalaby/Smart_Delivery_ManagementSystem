from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from apps.complaints.services import create_complaint
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.shipments.models import Shipment
from apps.shipments.services import create_shipment

from .forms import (
    ComplaintForm,
    LoginForm,
    ProfileForm,
    RegisterForm,
    ShipmentForm,
    StyledPasswordChangeForm,
)


def dashboard_url(user):
    name = {"MANAGER": "manager:dashboard", "DRIVER": "driver:dashboard"}.get(
        user.role, "customer:dashboard"
    )
    return reverse(name)


def profile_url(user):
    name = {"MANAGER": "manager:profile", "DRIVER": "driver:profile"}.get(
        user.role, "accounts:profile"
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


# ---------------- customer: shipments & complaints ----------------
BASE_FEE = Decimal("30.00")
PER_KG_FEE = Decimal("5.00")


def calculate_delivery_fee(weight):
    return (BASE_FEE + PER_KG_FEE * Decimal(weight)).quantize(Decimal("0.01"))


class CustomerOnlyMixin(LoginRequiredMixin):
    def dispatch(self, request, *a, **kw):
        u = request.user
        if u.is_authenticated and u.role != "CUSTOMER":
            return redirect(dashboard_url(u))
        return super().dispatch(request, *a, **kw)


class NewShipmentView(CustomerOnlyMixin, FormView):
    template_name = "customer/create_shipment.html"
    form_class = ShipmentForm

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            shipment = create_shipment(
                customer=self.request.user,
                delivery_fee=calculate_delivery_fee(data["package_weight"]),
                **data,
            )
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.form_invalid(form)
        messages.success(
            self.request,
            f"Shipment {shipment.tracking_number} created successfully.",
        )
        return redirect("customer:shipments")


class CustomerShipmentsView(CustomerOnlyMixin, TemplateView):
    template_name = "customer/shipments.html"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET
        qs = Shipment.objects.filter(customer=self.request.user)

        q = g.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(tracking_number__icontains=q)
                | Q(pickup_address__icontains=q)
                | Q(delivery_address__icontains=q)
                | Q(package_description__icontains=q)
            )

        status = g.get("status")
        if status in Shipment.Status.values:
            qs = qs.filter(status=status)

        date_from = parse_date(g.get("date_from", ""))
        date_to = parse_date(g.get("date_to", ""))
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        page_obj = Paginator(qs, self.paginate_by).get_page(g.get("page"))
        ctx["page_obj"] = page_obj
        ctx["shipments"] = page_obj.object_list
        return ctx


class NewComplaintView(CustomerOnlyMixin, FormView):
    template_name = "customer/create_complaint.html"
    form_class = ComplaintForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            complaint = create_complaint(
                customer=self.request.user, **form.cleaned_data
            )
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.form_invalid(form)
        messages.success(
            self.request, f"Complaint #{complaint.pk} submitted successfully."
        )
        return redirect("customer:complaints")


# ---------------- profile & password (all roles) ----------------
class ProfileView(LoginRequiredMixin, FormView):
    form_class = ProfileForm
    templates = {
        "CUSTOMER": "customer/profile.html",
        "DRIVER": "driver/profile.html",
        "MANAGER": "manager/profile.html",
    }

    def get_template_names(self):
        return [self.templates[self.request.user.role]]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # نسخة منفصلة من المستخدم علشان request.user ما يتغيرش لو الفورم فيه أخطاء
        kwargs["instance"] = get_user_model().objects.get(pk=self.request.user.pk)
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Your profile has been updated.")
        return redirect(profile_url(self.request.user))


class PasswordChangePage(LoginRequiredMixin, FormView):
    template_name = "auth/change_password.html"
    form_class = StyledPasswordChangeForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["back_url"] = profile_url(self.request.user)
        return ctx

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)  # يفضل مسجل دخول بعد تغيير الباسورد
        messages.success(self.request, "Your password has been changed.")
        return redirect(profile_url(user))


class CustomerDashboardView(CustomerOnlyMixin, TemplateView):
    template_name = "customer/dashboard.html"

    ACTIVE = [
        Shipment.Status.ASSIGNED,
        Shipment.Status.PICKED_UP,
        Shipment.Status.IN_TRANSIT,
        Shipment.Status.OUT_FOR_DELIVERY,
    ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        shipments = Shipment.objects.filter(customer=user)

        ctx["total_shipments"] = shipments.count()
        ctx["pending_shipments"] = shipments.filter(status=Shipment.Status.PENDING).count()
        ctx["active_shipments"] = shipments.filter(status__in=self.ACTIVE).count()
        ctx["delivered_shipments"] = shipments.filter(status=Shipment.Status.DELIVERED).count()

        ctx["recent_shipments"] = shipments[:5]
        ctx["active_shipment"] = shipments.filter(
            status__in=[Shipment.Status.PENDING, *self.ACTIVE]
        ).first()
        ctx["recent_payments"] = (
            Payment.objects.filter(customer=user).select_related("shipment")[:5]
        )
        ctx["recent_notifications"] = Notification.objects.filter(recipient=user)[:5]
        return ctx