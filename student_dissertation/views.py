from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, DestroyAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Course, YearOfStudy, Student, Document, Consultation, Announcement, Feedback, Milestone, Stage, ProjectGroup, FileRepository
from .serializers import CourseSerializer, YearOfStudySerializer, StudentSerializer, DocumentSerializer, ConsultationSerializer, AnnouncementSerializer, FeedbackSerializer, MilestoneSerializer, StageSerializer, StudentBasicSerializer, ProjectGroupSerializer, FileRepositorySerializer
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from collections import defaultdict
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import ValidationError


class CourseListView(ListAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]


class YearListView(ListAPIView):
    queryset = YearOfStudy.objects.all()
    serializer_class = YearOfStudySerializer
    permission_classes = [AllowAny]


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StudentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Student registered successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        reg_number = request.data.get("reg_number")
        password = request.data.get("password")

        if not reg_number or not password:
            return Response({"error": "Both registration number and password are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=reg_number, password=password)

        if user is not None:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"token": token.key}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        groups = list(user.groups.values_list('name', flat=True))

        return Response({
            "username": user.username,
            "email": user.email,
            "role": groups[0] if groups else "User",
        })


class StudentProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            student = Student.objects.get(user=user)
            groups = student.project_groups.all()
            is_in_group = groups.exists()
            is_group_leader = groups.filter(leader=student).exists()

            return Response({
                "full_name": student.full_name,
                "reg_number": student.reg_number,
                "project_title": student.project_title,
                "supervisor": student.supervisor.username if student.supervisor else "Not Assigned",
                "is_in_group": is_in_group,
                "is_group_leader": is_group_leader,
                "group_id": groups.first().id if is_in_group else None,
                "group_name": groups.first().name if is_in_group else None,
            })
        except Student.DoesNotExist:
            return Response({"error": "Student profile not found"}, status=404)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not user.check_password(current_password):
            return Response({"error": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({'error': 'Invalid email'}, status=status.HTTP_401_UNAUTHORIZED)

        user = authenticate(request, username=user.username, password=password)
        if not user or not user.is_active:
            return Response({'error': 'Invalid password or inactive account'}, status=status.HTTP_401_UNAUTHORIZED)

        # 🔄 Refresh from DB to get updated groups
        user = User.objects.get(id=user.id)

        if user.groups.filter(name='Admin').exists():
            role = 'admin'
        elif user.groups.filter(name='Supervisor').exists():
            role = 'supervisor'
        else:
            return Response({
                'error': 'User has no role assigned',
                'groups': list(user.groups.values_list('name', flat=True))
            }, status=status.HTTP_403_FORBIDDEN)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'message': 'Login successful',
            'role': role,
            'username': user.username,
            'token': token.key,
        }, status=status.HTTP_200_OK)


class CreateSupervisorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.groups.filter(name='Admin').exists():
            return Response({'error': 'Unauthorized access.'}, status=status.HTTP_403_FORBIDDEN)

        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')

        if not all([username, email, password]):
            return Response({'error': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, email=email, password=password)

        # Add to Supervisor group
        supervisor_group, _ = Group.objects.get_or_create(name="Supervisor")
        user.groups.add(supervisor_group)

        return Response({'message': f"Supervisor {username} created successfully."}, status=status.HTTP_201_CREATED)


class StudentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not user.groups.filter(name='Admin').exists():
            return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)

        students = Student.objects.all()
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GroupedStudentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        students = Student.objects.select_related('course', 'year_of_study')
        grouped = defaultdict(lambda: defaultdict(list))  # course -> year -> students list

        for student in students:
            if student.course and student.year_of_study:
                course_name = student.course.name
                year_name = student.year_of_study.year

                grouped[course_name][year_name].append(student)

        response_data = []

        for course_name, years in grouped.items():
            for year_name, student_list in years.items():
                serialized_students = StudentBasicSerializer(student_list, many=True).data
                response_data.append({
                    'course': course_name,
                    'year': year_name,
                    'students': serialized_students
                })

        return Response(response_data)


class AutoCreateGroupsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        course_id = request.data.get('course_id')
        year_id = request.data.get('year_id')
        group_size = int(request.data.get('group_size', 4))
        base_name = request.data.get('base_name', 'Group')

        students = Student.objects.filter(course_id=course_id, year_of_study_id=year_id).order_by('reg_number')

        if not students.exists():
            return Response({'message': 'No students found for this course and year.'}, status=status.HTTP_404_NOT_FOUND)

        student_list = list(students)
        total = len(student_list)
        group_count = 0
        created_groups = []

        for i in range(0, total, group_size):
            group_count += 1
            group_students = student_list[i:i+group_size]
            group_name = f"{base_name} {group_count}"

            group = ProjectGroup.objects.create(
                name=group_name,
                course_id=course_id,
                year_id=year_id,
                project_title=""
            )
            group.members.set(group_students)
            created_groups.append(group_name)

        return Response({'message': f'{len(created_groups)} groups created.', 'groups': created_groups}, status=status.HTTP_201_CREATED)


class ProjectGroupListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        groups = ProjectGroup.objects.all().select_related('course', 'year').prefetch_related('members')
        serializer = ProjectGroupSerializer(groups, many=True)
        return Response(serializer.data)


class ProjectGroupDeleteView(DestroyAPIView):
    queryset = ProjectGroup.objects.all()
    serializer_class = ProjectGroupSerializer
    permission_classes = [IsAuthenticated]


class ProjectGroupDetailView(RetrieveUpdateDestroyAPIView):
    queryset = ProjectGroup.objects.all()
    serializer_class = ProjectGroupSerializer
    permission_classes = [IsAuthenticated]


class MyGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student  # Assuming you have a one-to-one `User -> Student`
        group = ProjectGroup.objects.filter(members=student).select_related('course', 'year').prefetch_related('members').first()

        if group:
            serializer = ProjectGroupSerializer(group)
            return Response(serializer.data)
        return Response({'detail': 'No group found for this student'}, status=404)


class RegisterProjectTitleView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        project_title = request.data.get('project_title')

        try:
            student = Student.objects.get(user=request.user)
            # ❌ Block if student is already in a group
            if student.project_groups.exists():
                return Response({
                    'error': 'You are part of a project group. Title must be registered through the group leader.'
                }, status=status.HTTP_403_FORBIDDEN)
            student.project_title = project_title
            student.save()

            return Response({'message': 'Project title registered successfully'}, status=status.HTTP_200_OK)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)


class RegisterGroupProjectTitleView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        project_title = request.data.get('project_title')

        try:
            student = Student.objects.get(user=request.user)

            # Check if student is group leader
            group = ProjectGroup.objects.filter(leader=student).first()
            if not group:
                return Response(
                    {'error': 'Only group leaders can register a group project title.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            group.project_title = project_title
            group.save()

            return Response({'message': 'Group project title registered successfully.'}, status=status.HTTP_200_OK)

        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)


class StudentsWithoutGroupsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Filter students who are not in any project group
        students_without_groups = Student.objects.filter(
            ~Q(project_groups__isnull=False)
        ).distinct()

        serializer = StudentSerializer(students_without_groups, many=True)
        return Response(serializer.data)


class AssignSupervisorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Check if the user is an Admin
        if not user.groups.filter(name='Admin').exists():
            return Response({'error': 'Unauthorized access.'}, status=status.HTTP_403_FORBIDDEN)

        # Get the data from the request
        reg_number = request.data.get('reg_number')
        supervisor_id = request.data.get('supervisor_id')
        force = request.data.get('force', False)

        if not reg_number or not supervisor_id:
            return Response({'error': 'reg_number and supervisor_id are required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            # Query to ensure the student is not part of any group
            student = Student.objects.get(reg_number=reg_number, project_groups__isnull=True)
            supervisor = User.objects.get(id=supervisor_id, groups__name="Supervisor")

            # Check if the student already has a supervisor
            if student.supervisor and not force:
                return Response(
                    {
                        'error': f"{student.full_name} already has a supervisor assigned.",
                        'requires_confirmation': True
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Assign the supervisor to the student
            student.supervisor = supervisor
            student.save()
            return Response(
                {'message': f"Supervisor {supervisor.username} successfully assigned to {student.full_name}."},
                status=status.HTTP_200_OK,
            )
        except Student.DoesNotExist:
            return Response({'error': 'Student not found or already in a group'}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({'error': 'Supervisor not found or not in Supervisor group'},
                            status=status.HTTP_404_NOT_FOUND)


class AssignGroupSupervisorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Check if the user is an admin
        if not user.groups.filter(name='Admin').exists():
            return Response({'error': 'Unauthorized access.'}, status=status.HTTP_403_FORBIDDEN)

        group_id = request.data.get('group_id')
        supervisor_id = request.data.get('supervisor_id')
        force = request.data.get('force', False)

        # Ensure required data is provided
        if not group_id or not supervisor_id:
            return Response(
                {'error': 'group_id and supervisor_id are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Retrieve the group and supervisor
            group = ProjectGroup.objects.get(id=group_id)
            supervisor = User.objects.get(id=supervisor_id, groups__name="Supervisor")

            # Check if the group already has a supervisor
            if group.supervisor and not force:
                return Response(
                    {
                        'error': f"The group already has a supervisor assigned.",
                        'requires_confirmation': True
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Assign the supervisor to the group
            group.supervisor = supervisor
            group.save()

            return Response(
                {'message': f"Supervisor {supervisor.username} successfully assigned to the group."},
                status=status.HTTP_200_OK
            )
        except ProjectGroup.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({'error': 'Supervisor not found or not in Supervisor group'},
                            status=status.HTTP_404_NOT_FOUND)


class SupervisorListView(APIView):
    def get(self, request):
        supervisors = User.objects.filter(groups__name="Supervisor")
        data = [{'id': s.id, 'username': s.username, 'email': s.email} for s in supervisors]
        return Response(data)


class AssignedStudentsView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        supervisor = request.user
        students = Student.objects.filter(supervisor=supervisor)
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)


class AssignedGroupsView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        supervisor = request.user
        groups = ProjectGroup.objects.filter(supervisor=supervisor)
        serializer = ProjectGroupSerializer(groups, many=True)
        return Response(serializer.data)


class AssignedSupervisorView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            student = Student.objects.get(user=request.user)

            if not student.supervisor:
                return Response({'error': 'No supervisor assigned yet.'}, status=status.HTTP_404_NOT_FOUND)

            supervisor_data = {
                'id': student.supervisor.id,
                'username': student.supervisor.username,
                'email': student.supervisor.email,
            }
            return Response(supervisor_data, status=status.HTTP_200_OK)

        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class AssignedGroupSupervisorView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get the logged-in student's profile
            student = Student.objects.get(user=request.user)

            # Ensure the student is part of exactly one project group
            project_group = student.project_groups.first()
            if not project_group:
                return Response({'error': 'You are not assigned to any project group.'}, status=status.HTTP_404_NOT_FOUND)

            # Check if the group has a supervisor assigned
            if not project_group.supervisor:
                return Response({'error': 'No supervisor assigned to your group yet.'}, status=status.HTTP_404_NOT_FOUND)

            # Prepare supervisor data
            supervisor_data = {
                'group_name': project_group.name,
                'supervisor_id': project_group.supervisor.id,
                'supervisor_username': project_group.supervisor.username,
                'supervisor_email': project_group.supervisor.email,
            }

            return Response(supervisor_data, status=status.HTTP_200_OK)

        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UploadStudentDocumentView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data.copy()

        # Assuming the document is related to the Student model instance of the logged-in user
        student = request.user.student  # Adjust if your user model has a student relation

        content_type = ContentType.objects.get_for_model(student)

        data['content_type'] = content_type.pk  # Pass the pk of content type
        data['object_id'] = student.pk          # Pass the student's pk as object id

        serializer = DocumentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class UploadGroupDocumentView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        project_title = request.data.get('title')
        file = request.data.get('file')
        supervisor = request.data.get('supervisor')

        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        group = ProjectGroup.objects.filter(leader=student).first()
        if not group:
            return Response({'error': 'Only group leaders can upload group documents.'}, status=status.HTTP_403_FORBIDDEN)

        if not project_title or not file:
            return Response({'error': 'Title and file are required.'}, status=status.HTTP_400_BAD_REQUEST)

        content_type = ContentType.objects.get_for_model(ProjectGroup)

        data = {
            'title': project_title,
            'file': file,
            'content_type': content_type.id,
            'object_id': group.id,
            'student': student.id,
            'supervisor': supervisor
        }

        serializer = DocumentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Group document uploaded successfully'}, status=status.HTTP_201_CREATED)

        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class SupervisorDocumentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        supervisor = request.user

        if not supervisor.groups.filter(name='Supervisor').exists():
            return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

        documents = Document.objects.filter(supervisor=supervisor)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookConsultationView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Extract registration number from query parameters
        reg_number = request.query_params.get('reg_number')

        if not reg_number:
            return Response({'error': 'Registration number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the student associated with the provided registration number
        student = get_object_or_404(Student, reg_number=reg_number)

        # Ensure the student has a supervisor assigned
        supervisor = student.supervisor
        if not supervisor:
            return Response({'error': 'Student does not have a supervisor assigned.'}, status=status.HTTP_400_BAD_REQUEST)

        # Prepare the data for the consultation
        data = request.data.copy()
        data['student'] = student.id
        data['supervisor'] = supervisor.id

        # Serialize the consultation data
        serializer = ConsultationSerializer(data=data)
        if serializer.is_valid():
            # Save the consultation to the database
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ManageConsultationView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        email = request.query_params.get("email")
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            consultations = Consultation.objects.filter(supervisor__email=email)

            serializer = ConsultationSerializer(consultations, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Consultation.DoesNotExist:
            return Response({'error': 'No consultations found for this supervisor.'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        email = request.query_params.get("email")
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            consultation = Consultation.objects.get(id=pk)
            status = request.data.get('status')

            consultation.status = status
            consultation.save()

            return Response({"message": "Consultation status updated successfully."}, status=status.HTTP_200_OK)

        except Consultation.DoesNotExist:
            return Response({'error': 'Consultation not found.'}, status=status.HTTP_404_NOT_FOUND)


class StudentConsultationView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reg_number = request.query_params.get("regNumber")

        if not reg_number:
            return Response({"error": "Student registration number is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch consultations for the student using reg_number
        consultations = Consultation.objects.filter(student__reg_number=reg_number)
        if not consultations:
            return Response({"error": "No consultations found for this registration number."}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the consultations and return them
        serializer = ConsultationSerializer(consultations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        supervisor = request.user

        if not supervisor.groups.filter(name='Supervisor').exists():
            return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)

        announcements = Announcement.objects.filter(supervisor=supervisor).order_by('-created_at')
        serializer = AnnouncementSerializer(announcements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        supervisor = request.user

        if not supervisor.groups.filter(name='Supervisor').exists():
            return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)

        serializer = AnnouncementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(supervisor=supervisor)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentAnnouncementView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            return Response({"error": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # Supervisor announcements for individual student
        supervisor_announcements = Announcement.objects.filter(supervisor=student.supervisor)

        # Fetch all groups the student belongs to
        groups = ProjectGroup.objects.filter(members=student)

        # Announcements for groups the student belongs to
        group_supervisor_announcements = Announcement.objects.filter(
            supervisor__in=[group.supervisor for group in groups]
        )

        # Global admin announcements for all students
        admin_announcements = Announcement.objects.filter(
            admin__isnull=False,
            target_group="students"
        )

        # Combine all announcements
        all_announcements = list(supervisor_announcements) + list(group_supervisor_announcements) + list(admin_announcements)
        all_announcements = sorted(all_announcements, key=lambda x: x.created_at, reverse=True)

        # Serialize and return the response
        serializer = AnnouncementSerializer(all_announcements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminAnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not user.groups.filter(name='Admin').exists():
            return Response({"error": "Unauthorized access."}, status=status.HTTP_403_FORBIDDEN)

        announcements = Announcement.objects.filter(admin=user).order_by('-created_at')
        serializer = AnnouncementSerializer(announcements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user

        if not user.groups.filter(name='Admin').exists():
            return Response({"error": "Unauthorized access."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AnnouncementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(admin=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GiveFeedbackView(APIView):
    def post(self, request):
        supervisor = request.user
        reg_number = request.data.get('reg_number')
        content = request.data.get('content')
        is_group = request.data.get('is_group', False)

        if not reg_number or not content:
            return Response({'error': 'reg_number and content are required.'}, status=400)

        student = get_object_or_404(Student, reg_number=reg_number)

        if is_group in [True, "true", "1", 1]:
            group = ProjectGroup.objects.filter(leader=student).first()
            if not group:
                return Response({"error": "You're not a group leader."}, status=403)
            content_type = ContentType.objects.get_for_model(ProjectGroup)
            object_id = group.id
            supervisor = group.supervisor
        else:
            if not student.supervisor:
                return Response({"error": "This student has no supervisor assigned."}, status=400)
            content_type = ContentType.objects.get_for_model(Student)
            object_id = student.id
            supervisor = student.supervisor

        data = {
            "supervisor": supervisor.id,
            "student": student.id,
            "content": content,
            "content_type": content_type.id,
            "object_id": object_id
        }

        serializer = FeedbackSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)


class ViewFeedbackView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        feedbacks = Feedback.objects.filter(student=student).order_by('-created_at')
        serializer = FeedbackSerializer(feedbacks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateStageView(APIView):
    permission_classes = [IsAuthenticated]
    """
    View for managing stages (Admin functionality).
    """
    def get(self, request):
        """
        Retrieve all stages.
        """
        stages = Stage.objects.all()
        serializer = StageSerializer(stages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a new stage.
        """
        data = request.data
        serializer = StageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, stage_id):
        """
        Delete a stage by ID.
        """
        try:
            stage = Stage.objects.get(id=stage_id)
            stage.delete()
            return Response({"message": "Stage deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Stage.DoesNotExist:
            return Response({"error": "Stage not found."}, status=status.HTTP_404_NOT_FOUND)


class ProgressTrackingView(APIView):
    """
    View for managing progress tracking for students and supervisors.
    Supervisors can view and update milestones for students or groups they supervise.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Retrieve milestones. Supervisors see milestones they supervise.
        """
        if not request.user.groups.filter(name='Supervisor').exists():
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        # Retrieve milestones for students or groups supervised by the user
        milestones = Milestone.objects.filter(supervisor=request.user)
        serializer = MilestoneSerializer(milestones, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a new milestone for a student or group. Only supervisors can create milestones.
        """
        data = request.data.copy()
        reg_number = data.get('student')
        group_id = data.get('group')
        stage_id = data.get('stage')

        # Ensure either student or group is provided (but not both)
        if not reg_number and not group_id:
            return Response({"error": "Either student or group must be specified."}, status=status.HTTP_400_BAD_REQUEST)
        if reg_number and group_id:
            return Response({"error": "Specify either student or group, not both."}, status=status.HTTP_400_BAD_REQUEST)

        if reg_number:
            student = get_object_or_404(Student, id=reg_number)
            data['student'] = student.id

        if group_id:
            group = get_object_or_404(ProjectGroup, id=group_id)
            if group.supervisor != request.user:
                return Response({"error": "You are not authorized to manage milestones for this group."}, status=status.HTTP_403_FORBIDDEN)
            data['group'] = group.id

        if not Stage.objects.filter(id=stage_id).exists():
            return Response({"error": "Invalid stage ID."}, status=status.HTTP_400_BAD_REQUEST)

        data['supervisor'] = request.user.id  # Assign current user as supervisor
        serializer = MilestoneSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, milestone_id=None):
        """
        Update an existing milestone's details. Only the supervisor who created it can update it.
        """
        if not milestone_id:
            return Response({"error": "Milestone ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        milestone = get_object_or_404(Milestone, id=milestone_id)

        # Ensure that only the supervisor who created the milestone can update it
        if milestone.supervisor != request.user:
            return Response({"error": "You are not authorized to update this milestone."}, status=status.HTTP_403_FORBIDDEN)

        # Update the milestone
        serializer = MilestoneSerializer(milestone, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentMilestoneView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = getattr(request.user, 'student', None)
        if not student:
            return Response({'error': 'Only students can access this.'}, status=403)

        # Get individual milestones for the student
        individual_milestones = Milestone.objects.filter(student=student)

        # Determine the student's group by querying the ProjectGroup model
        group = ProjectGroup.objects.filter(members=student).first()  # Adjust `students` to your field name

        # Get group milestones if the student belongs to a group
        group_milestones = Milestone.objects.filter(group=group) if group else Milestone.objects.none()

        # Combine both individual and group milestones
        milestones = individual_milestones | group_milestones
        serializer = MilestoneSerializer(milestones, many=True)

        return Response(serializer.data)


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user
        file = request.FILES.get('file')
        file_type = request.data.get('file_type')
        description = request.data.get('description')
        student = None
        group = None

        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if a group is specified
        group_id = request.data.get('group_id')
        if group_id:
            try:
                group = ProjectGroup.objects.get(id=group_id)
                if not group.members.filter(id=student.id).exists():
                    return Response({"error": "You are not a member of this group."}, status=status.HTTP_403_FORBIDDEN)
            except ProjectGroup.DoesNotExist:
                return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

        # Create the FileRepository instance
        try:
            file_repo = FileRepository.objects.create(
                student=student if not group else None,
                group=group,
                file=file,
                file_type=file_type,
                description=description
            )
            return Response(FileRepositorySerializer(file_repo).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminRepositoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        file_type = request.query_params.get('file_type')
        year = request.query_params.get('year')  # 👈 support year filtering

        files = FileRepository.objects.all()

        if file_type:
            files = files.filter(file_type=file_type)
        if year:
            files = files.filter(year=year)

        serializer = FileRepositorySerializer(files, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        file = get_object_or_404(FileRepository, pk=pk)
        serializer = FileRepositorySerializer(file, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
