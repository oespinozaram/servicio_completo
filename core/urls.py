from django.urls import path
from . import webhooks, views

app_name = 'core'

urlpatterns = [
    path('webhook/telegram/', webhooks.webhook_telegram, name='webhook_telegram'),
    path('demo/solicitar/', views.solicitar_demo, name='solicitar_demo'),
]