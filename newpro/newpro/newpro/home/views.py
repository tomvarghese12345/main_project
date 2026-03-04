from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings


def home(request):
    return render(request, 'home/home.html')


def about(request):
    return render(request, 'home/about.html')


def developer(request):
    return render(request, 'home/developer.html')


def contact(request):
    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        message = request.POST.get('message')

        full_message = f"""
        New Contact Form Message

        Name: {name}
        Phone: {phone}
        Email: {email}

        Message:
        {message}
        """

        send_mail(
            subject="New Contact Message - NewPro",
            message=full_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=['tomv7560@gmail.com'],
            fail_silently=False,
        )

        return render(request, 'home/contact.html', {'success': True})

    return render(request, 'home/contact.html')
