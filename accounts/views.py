from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import MemberProfileForm, RegistrationForm, UserProfileForm
from Forum_Events.models import MemberProfile


class SignUpView(CreateView):
    form_class = RegistrationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("forum:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Votre compte a ete cree.")
        return response


@login_required
def profile(request, username=None):
    if username:
        profile_user = get_object_or_404(get_user_model(), username=username)
    else:
        profile_user = request.user

    member_profile, _ = MemberProfile.objects.get_or_create(user=profile_user)
    context = {
        "profile": profile_user,
        "member_profile": member_profile,
        "is_owner": request.user.is_authenticated and request.user.pk == profile_user.pk,
    }
    return render(request, "registration/profile.html", context)


@login_required
def profile_edit(request):
    member_profile, _ = MemberProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = UserProfileForm(request.POST, instance=request.user)
        profile_form = MemberProfileForm(request.POST, request.FILES, instance=member_profile)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile_form.save()
            messages.success(request, "Votre profil a ete mis a jour.")
            return redirect("accounts:profile")
    else:
        user_form = UserProfileForm(instance=request.user)
        profile_form = MemberProfileForm(instance=member_profile)

    return render(
        request,
        "registration/profile_edit.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        user_id = user.pk
        from django.contrib.auth import logout
        logout(request)
        get_user_model().objects.filter(pk=user_id).delete()
        messages.success(request, "Votre compte a ete definitivement supprimé.")
        return redirect("home")

    return render(request, "registration/account_delete.html")
