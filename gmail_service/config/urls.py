from django.urls import path
from inbox.views import index, email_detail

urlpatterns = [
    path('', index, name='inbox'),
    path('mail-detail/<str:email_id>/', email_detail, name='email-detail'),
]
