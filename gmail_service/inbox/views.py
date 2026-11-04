from django.http import JsonResponse
from django.shortcuts import render
from .services import get_emails, get_email


def index(request):
    emails, error = get_emails()
    return render(request, 'inbox/index.html', {'emails': emails, 'data_error': error})


def email_detail(request, email_id):
    if request.method != 'GET':
        response = JsonResponse({'error': 'Yalnızca GET isteği kabul edilir.'}, status=405)
        response['Allow'] = 'GET'
        return response
    email, error, status = get_email(email_id)
    return JsonResponse({'error': error} if error else email, status=status)
