from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Student, Notification, Document


@receiver(pre_save, sender=Student)
def notify_supervisor_assignment(sender, instance, **kwargs):
    try:
        previous = Student.objects.get(pk=instance.pk)
        changed = previous.supervisor != instance.supervisor
    except Student.DoesNotExist:
        changed = True  # New student

    if changed and instance.supervisor:
        # Save notification in DB
        Notification.objects.create(
            recipient=instance.supervisor,
            message=f"You have been assigned a new student: {instance.full_name} ({instance.reg_number})"
        )

        # Send email notification
        send_mail(
            subject="New Student Assignment Notification",
            message=f"Dear {instance.supervisor.get_full_name() or instance.supervisor.username},\n\n"
                    f"You have been assigned a new student:\n\n"
                    f"Name: {instance.full_name}\n"
                    f"Reg No: {instance.reg_number}\n"
                    f"Project Title: {instance.project_title or 'N/A'}\n\n"
                    f"Please log in to your dashboard to view more details.",
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=[instance.supervisor.email],
            fail_silently=False,
        )


@receiver(post_save, sender=Document)
def notify_supervisor_document_upload(sender, instance, created, **kwargs):
    if not created:
        return

    owner = instance.owner

    # Check if the owner is a Student
    if isinstance(owner, Student) and instance.supervisor:
        student = owner
        supervisor = instance.supervisor

        # Save notification in DB
        Notification.objects.create(
            recipient=supervisor,
            message=f"{student.full_name} has uploaded a new document: {instance.title}"
        )

        # Send email
        send_mail(
            subject="Student Document Upload Notification",
            message=f"Dear {supervisor.get_full_name() or supervisor.username},\n\n"
                    f"Your student {student.full_name} ({student.reg_number}) has uploaded a new document:\n"
                    f"Title: {instance.title}\n\n"
                    f"Please log in to your dashboard to review it.",
            from_email=None,
            recipient_list=[supervisor.email],
            fail_silently=False,
        )
