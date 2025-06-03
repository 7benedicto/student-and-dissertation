from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from .views import GroupedStudentView, AutoCreateGroupsView, ProjectGroupListView, ProjectGroupDeleteView, ProjectGroupDetailView, MyGroupView, CourseListView, YearListView, RegisterView, LoginView, AdminLoginView, StudentListView, RegisterProjectTitleView, RegisterGroupProjectTitleView, StudentsWithoutGroupsView, AssignSupervisorView, AssignGroupSupervisorView, SupervisorListView, AssignedStudentsView, AssignedGroupsView, AssignedSupervisorView, AssignedGroupSupervisorView, UploadStudentDocumentView, UploadGroupDocumentView, SupervisorDocumentListView, BookConsultationView, ManageConsultationView, StudentConsultationView, AnnouncementView, StudentAnnouncementView, AdminAnnouncementView, GiveFeedbackView, ViewFeedbackView, ChangePasswordView, CreateSupervisorView, UserProfileView, StudentProfileView, ProgressTrackingView, CreateStageView, StudentMilestoneView, FileUploadView, AdminRepositoryView
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet


router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('token-login/', obtain_auth_token, name='token-login'),
    path('courses/', CourseListView.as_view(), name='course-list'),
    path('years/', YearListView.as_view(), name='year-list'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('user-profile/', UserProfileView.as_view(), name='user-profile'),
    path('student-profile/', StudentProfileView.as_view(), name='student-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('admin-login/', AdminLoginView.as_view(), name='admin-login'),
    path('create-supervisor/', CreateSupervisorView.as_view(), name='create-supervisor'),
    path('students/', StudentListView.as_view(), name='student-list'),
    path('grouped-students/', GroupedStudentView.as_view(), name='grouped-students'),
    path('auto-create-groups/', AutoCreateGroupsView.as_view(), name='create-groups'),
    path('project-groups/', ProjectGroupListView.as_view(), name='project-group-list'),
    # path('project-groups/<int:pk>/', ProjectGroupDeleteView.as_view(), name='delete-group'),
    path('project-groups/<int:pk>/', ProjectGroupDetailView.as_view(), name='project-group-detail'),
    path('my-group/', MyGroupView.as_view(), name='my-group'),
    path('register-title/', RegisterProjectTitleView.as_view(), name='register-title'),
    path('register-group-title/', RegisterGroupProjectTitleView.as_view(), name='register-group-title'),
    path('students-without-groups/', StudentsWithoutGroupsView.as_view(), name='students-without-groups'),
    path('assign-supervisor/', AssignSupervisorView.as_view(), name='assign-supervisor'),
    path('assign-group-supervisor/', AssignGroupSupervisorView.as_view(), name='assign-group-supervisor'),
    path('supervisors/', SupervisorListView.as_view(), name='supervisor-list'),
    path('assigned-students/', AssignedStudentsView.as_view(), name='assigned-students'),
    path('assigned-groups/', AssignedGroupsView.as_view(), name='assigned-students'),
    path('assigned-supervisor/', AssignedSupervisorView.as_view(), name='assigned-supervisor'),
    path('assigned-group-supervisor/', AssignedGroupSupervisorView.as_view(), name='assigned-supervisor'),
    path('upload-student-document/', UploadStudentDocumentView.as_view(), name='upload-student-document'),
    path('upload-group-document/', UploadGroupDocumentView.as_view(), name='upload-group-document'),
    path('supervisor-documents/', SupervisorDocumentListView.as_view(), name='supervisor-documents'),
    path('book-consultation/', BookConsultationView.as_view(), name='book-consultation'),
    path('manage-consultation/', ManageConsultationView.as_view(), name='manage-consultation'),
    path('manage-consultation/<int:pk>/', ManageConsultationView.as_view(), name='manage-consultation'),
    path('student-consultations/', StudentConsultationView.as_view(), name='student-consultations'),
    path('announcements/', AnnouncementView.as_view(), name='announcements'),
    path('student-announcements/', StudentAnnouncementView.as_view(), name='student-announcements'),
    path('admin-announcements/', AdminAnnouncementView.as_view(), name='admin-announcements'),
    path('give-feedback/', GiveFeedbackView.as_view(), name='give-feedback'),
    path('view-feedback/', ViewFeedbackView.as_view(), name='view-feedback'),
    path('stages/', CreateStageView.as_view(), name='create-stage'),
    path('stages/<int:stage_id>/', CreateStageView.as_view(), name='delete-stage'),
    path('milestones/', ProgressTrackingView.as_view(), name='milestone-list'),
    path('milestones/student/<int:reg_number>/', ProgressTrackingView.as_view(), name='milestone-by-student'),
    path('milestones/<int:milestone_id>/', ProgressTrackingView.as_view(), name='milestone-update'),
    path('student/milestones/', StudentMilestoneView.as_view(), name='student-milestones'),
    path('upload/', FileUploadView.as_view(), name='student-file-upload'),
    path('repository/', AdminRepositoryView.as_view(), name='admin-repository'),
    path('repository/<int:pk>/', AdminRepositoryView.as_view()),
]
