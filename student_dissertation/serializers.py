from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from .models import Student, Document, Consultation, Announcement, Feedback, Milestone, Stage, Course, YearOfStudy, ProjectGroup, FileRepository, Notification


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name']


class YearOfStudySerializer(serializers.ModelSerializer):
    class Meta:
        model = YearOfStudy
        fields = ['id', 'year']


class StudentSerializer(serializers.ModelSerializer):
    reg_number = serializers.CharField()
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField()
    supervisor = serializers.SerializerMethodField()
    course = CourseSerializer(read_only=True)
    year_of_study = YearOfStudySerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(), source='course', write_only=True)
    year_id = serializers.PrimaryKeyRelatedField(queryset=YearOfStudy.objects.all(), source='year_of_study', write_only=True)

    class Meta:
        model = Student
        fields = ['id', 'reg_number', 'full_name', 'password', 'project_title', 'supervisor', 'course', 'year_of_study', 'course_id', 'year_id']

    def create(self, validated_data):
        reg_number = validated_data.pop('reg_number')
        password = validated_data.pop('password')
        full_name = validated_data.pop('full_name')
        course = validated_data.pop('course')
        year = validated_data.pop('year_of_study')

        # Create a User object with reg_number as the username
        user = User.objects.create_user(username=reg_number, password=password)

        # Create the Student object linked to the user
        student = Student.objects.create(user=user, reg_number=reg_number, full_name=full_name, course=course, year_of_study=year,)

        return student

    def get_supervisor(self, obj):
        if obj.supervisor:
            return {
                "username": obj.supervisor.username,
                "email": obj.supervisor.email
            }
        return None


class StudentBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['reg_number', 'full_name']


class SimpleStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'reg_number', 'full_name']


class ProjectGroupSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    year = YearOfStudySerializer(read_only=True)
    members = SimpleStudentSerializer(read_only=True, many=True)
    supervisor = serializers.SerializerMethodField()
    supervisor_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='supervisor', write_only=True, required=False)

    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(), source='course', write_only=True)
    year_id = serializers.PrimaryKeyRelatedField(queryset=YearOfStudy.objects.all(), source='year', write_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), source='members', many=True, write_only=True)

    class Meta:
        model = ProjectGroup
        fields = [
            'id', 'name', 'project_title',
            'course', 'year', 'members',      # For reading
            'course_id', 'year_id', 'member_ids',  # For writing
            'supervisor', 'supervisor_id'
        ]

    def get_supervisor(self, obj):  # MUST be outside the Meta class
        if obj.supervisor:
            return {
                "username": obj.supervisor.username,
                "email": obj.supervisor.email
            }
        return None


class DocumentSerializer(serializers.ModelSerializer):
    supervisor = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    content_type = serializers.PrimaryKeyRelatedField(required=False, queryset=ContentType.objects.all())
    object_id = serializers.IntegerField(required=False)

    full_name = serializers.SerializerMethodField()
    content_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'title', 'file', 'uploaded_at', 'supervisor', 'content_type', 'content_type_name', 'object_id', 'full_name']

    def get_full_name(self, obj):
        owner = obj.owner
        if isinstance(owner, Student):
            return owner.full_name  # or any name field on your Student model
        elif hasattr(owner, 'name'):  # assuming ProjectGroup has a "name" field
            return owner.name
        return "N/A"

    def validate_supervisor(self, value):
        if value:
            try:
                user = User.objects.get(username=value)
                return user
            except User.DoesNotExist:
                raise serializers.ValidationError("Supervisor not found.")
        return None

    def get_content_type_name(self, obj):
        return obj.content_type.model if obj.content_type else None


class ConsultationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    supervisor_name = serializers.CharField(source='supervisor.username', read_only=True)

    class Meta:
        model = Consultation
        fields = ['id','student', 'supervisor', 'student_name', 'supervisor_name', 'topic', 'proposed_date', 'status', 'created_at']

        extra_kwargs = {
            'student': {'write_only': True},
            'supervisor': {'write_only': True},
        }


class AnnouncementSerializer(serializers.ModelSerializer):
    supervisor_name = serializers.CharField(source='supervisor.username', read_only=True)

    class Meta:
        model = Announcement
        fields = ['id', 'title', 'content', 'target_group', 'supervisor_name', 'created_at', 'admin']


class FeedbackSerializer(serializers.ModelSerializer):
    supervisor_name = serializers.CharField(source='supervisor.username', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = Feedback
        fields = ['id', 'supervisor_name', 'student_name', 'content', 'content_type', 'object_id', 'created_at']


class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = ['id', 'name', 'description']


class MilestoneSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    supervisor_name = serializers.CharField(source='supervisor.username', read_only=True)
    stage_name = serializers.CharField(source='stage.name', read_only=True)

    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), required=False)
    group = serializers.PrimaryKeyRelatedField(queryset=ProjectGroup.objects.all(), required=False)
    stage = serializers.PrimaryKeyRelatedField(queryset=Stage.objects.all())

    class Meta:
        model = Milestone
        fields = ['id', 'student', 'student_name', 'group', 'group_name', 'supervisor', 'supervisor_name', 'milestone', 'status', 'completion_date', 'remarks', 'stage', 'stage_name']

        extra_kwargs = {
            'supervisor': {'write_only': True},
        }

    def validate(self, data):
        # Ensure that either 'student' or 'group' is provided, but not both
        student = data.get('student')
        group = data.get('group')
        if not student and not group:
            raise serializers.ValidationError("Either 'student' or 'group' must be specified.")
        if student and group:
            raise serializers.ValidationError("Specify either 'student' or 'group', not both.")
        return data


class FileRepositorySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', allow_null=True)
    group_name = serializers.CharField(source='group.name', allow_null=True)
    file = serializers.SerializerMethodField()

    class Meta:
        model = FileRepository
        fields = ['id', 'student', 'group', 'student_name', 'group_name', 'file', 'file_type', 'description', 'uploaded_at', 'version', 'year']

    def get_file(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.file.url)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
