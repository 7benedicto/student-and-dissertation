from django.apps import AppConfig


class StudentDissertationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'student_dissertation'

    def ready(self):
        import student_dissertation.signals # noqa: F401
