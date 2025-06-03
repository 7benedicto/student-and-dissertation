from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError


class StudentManager(BaseUserManager):
    def create_user(self, reg_number, password=None):
        if not reg_number:
            raise ValueError("Students must have a registration number")
        user = self.model(reg_number=reg_number)
        user.set_password(password)
        user.save(using=self._db)
        return user


class Course(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class YearOfStudy(models.Model):
    year = models.CharField(max_length=20)  # Example: "Year 1", "Year 2"

    def __str__(self):
        return self.year


class Student(AbstractBaseUser):
    reg_number = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    project_title = models.CharField(max_length=255, blank=True, null=True)  # New field
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    year_of_study = models.ForeignKey(YearOfStudy, on_delete=models.SET_NULL, null=True, blank=True)

    objects = StudentManager()

    USERNAME_FIELD = 'reg_number'

    def __str__(self):
        return self.reg_number


class ProjectGroup(models.Model):
    name = models.CharField(max_length=100)  # e.g. Group A
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    year = models.ForeignKey(YearOfStudy, on_delete=models.CASCADE)
    members = models.ManyToManyField(Student, related_name='project_groups')
    project_title = models.CharField(max_length=255, blank=True, null=True)
    leader = models.ForeignKey(Student, null=True, blank=True, on_delete=models.SET_NULL, related_name='leading_groups')
    supervisor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='supervised_groups')

    def __str__(self):
        return f"{self.name} - {self.course.name} (Year {self.year.year})"


class Project(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Polymorphic ownership
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    owner = GenericForeignKey('content_type', 'object_id')  # Can be Student or ProjectGroup

    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class FileRepository(models.Model):
    student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.CASCADE, related_name='files')
    group = models.ForeignKey(ProjectGroup, null=True, blank=True, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='student_projects/')
    file_type = models.CharField(max_length=50, choices=[('document', 'Document'), ('source_code', 'Source Code')])
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField(default=1)
    year = models.CharField(max_length=4, null=True, blank=True)

    def clean(self):
        if not self.student and not self.group:
            raise ValidationError("File must be linked to either a student or a group.")
        if self.student and self.group:
            raise ValidationError("File cannot be linked to both a student and a group.")


class Document(models.Model):
    # Generic relation to Student or ProjectGroup
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    owner = GenericForeignKey('content_type', 'object_id')

    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supervised_documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.owner}"


class Consultation(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='consultations')
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consultations')
    topic = models.CharField(max_length=255)
    proposed_date = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} ({self.student.full_name} -> {self.supervisor.username})"


class Announcement(models.Model):
    SUPERVISORS = 'supervisors'
    STUDENTS = 'students'
    TARGET_GROUP_CHOICES = [
        ('supervisors', 'Supervisors'),
        ('students', 'Students'),
    ]
    supervisor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="announcements")
    admin = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='admin_announcements')
    title = models.CharField(max_length=255)
    target_group = models.CharField(max_length=20, choices=TARGET_GROUP_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Feedback(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    owner = GenericForeignKey('content_type', 'object_id')

    supervisor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="feedback_given"
    )  # Supervisor giving the feedback
    student = models.ForeignKey(
        'Student', on_delete=models.CASCADE, related_name="feedback_received"
    )  # Student receiving the feedback
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.student.full_name}"


class Stage(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    # created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="stages_created")  # Admin user
    # created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Milestone(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True, related_name='milestones')
    group = models.ForeignKey(ProjectGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='group_milestones')
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supervisor_milestones')
    milestone = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    completion_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name='milestones')

    def __str__(self):
        target = self.student.full_name if self.student else f"Group: {self.group.name}"
        return f"{target} - {self.stage.name} - {self.status}"


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username}"
