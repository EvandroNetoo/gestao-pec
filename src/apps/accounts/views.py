from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django_htmx.http import HttpResponseClientRedirect

from accounts.forms import SigninForm, SignupForm, WidgetsShowcaseForm


@method_decorator(login_not_required, name='dispatch')
class SignupView(View):
    template_name = 'accounts/signup.html'
    form_class = SignupForm

    def get(self, request: HttpRequest):
        context = {
            'form': self.form_class(),
        }

        return render(request, self.template_name, context)

    def post(self, request: HttpRequest):
        form = self.form_class(request.POST)
        if not form.is_valid():
            context = {
                'form': form,
            }
            return render(
                request, 'components/django_form/index.html', context
            )

        user = form.save()
        login(request, user)

        return HttpResponseClientRedirect(reverse('home'))


@method_decorator(login_not_required, name='dispatch')
class SigninView(View):
    template_name = 'accounts/signin.html'
    form_class = SigninForm

    def get(self, request: HttpRequest):
        context = {
            'form': self.form_class(),
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest):
        form = self.form_class(request, request.POST)
        if not form.is_valid():
            print(form.errors)
            context = {
                'form': form,
            }

            return render(
                request, 'components/django_form/index.html', context
            )

        login(request, form.get_user())

        redirect_url = request.GET.get('next', '')
        return HttpResponseClientRedirect(
            redirect_url if redirect_url else reverse('home')
        )


class SignoutView(View):
    def post(self, request: HttpRequest):
        logout(request)
        return HttpResponseClientRedirect(reverse('signin'))



@login_not_required
def widgets_showcase(request: HttpRequest):
    form = WidgetsShowcaseForm({})
    form.is_valid()
    context = {
        'form': form,
    }
    return render(request, 'accounts/widgets_showcase.html', context)