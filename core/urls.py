from django.urls import path
from . import webhooks

app_name = 'core'

urlpatterns = [
    path('webhook/telegram/', webhooks.webhook_telegram, name='webhook_telegram'),
]