from django.contrib import admin
from .models import Student, Document, Consultation, Announcement, Feedback, Stage, Milestone, Course, YearOfStudy, ProjectGroup, Project, FileRepository

admin.site.register(Course)
admin.site.register(YearOfStudy)
admin.site.register(Student)
admin.site.register(Document)
admin.site.register(Consultation)
admin.site.register(Announcement)
admin.site.register(Feedback)
admin.site.register(Stage)
admin.site.register(Milestone)
admin.site.register(ProjectGroup)
admin.site.register(Project)
admin.site.register(FileRepository)
