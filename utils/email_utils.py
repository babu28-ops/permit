from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_template_email(subject, to_email, template_base, context):
    html_content = render_to_string(f'emails/{template_base}.html', context)
    text_content = render_to_string(f'emails/{template_base}.txt', context)
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.ADMIN_USER_EMAIL,
        to=[to_email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()