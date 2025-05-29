from django.contrib.auth.backends import BaseBackend
from .models import Student


class StudentBackend(BaseBackend):
    def authenticate(self, request, reg_number=None, password=None, **kwargs):
        try:
            student = Student.objects.get(reg_number=reg_number)
            if student.check_password(password):
                return student
        except Student.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Student.objects.get(pk=user_id)
        except Student.DoesNotExist:
            return None
