from django.conf import settings
from django.urls import path

from accounts import views

urlpatterns = [
    path('entrar/', views.SigninView.as_view(), name='signin'),
    path('sair/', views.SignoutView.as_view(), name='signout'),
]

if settings.DEBUG:
    urlpatterns += [
        path('widgets-showcase/', views.widgets_showcase, name='widgets_showcase'),
    ]