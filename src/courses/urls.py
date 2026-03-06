from django.urls import path

from . import views


urlpatterns = [
    # Choices for front-end selects
    path('choices/', views.CourseChoicesAPIView.as_view(), name='course-choices'),
    # Courses CRUD
    path('', views.CourseListCreateAPIView.as_view(), name='course-list-create'),
    path('<int:pk>/', views.CourseRetrieveUpdateDestroyAPIView.as_view(), name='course-detail'),
    # Modules CRUD (nested under course)
    path('<int:course_id>/modules/', views.CourseModuleListCreateAPIView.as_view(), name='coursemodule-list-create'),
    path(
        '<int:course_id>/modules/<int:pk>/',
        views.CourseModuleRetrieveUpdateDestroyAPIView.as_view(),
        name='coursemodule-detail',
    ),
    path('<int:course_id>/reviews/', views.CourseReviewListCreateAPIView.as_view(), name='course-review-list-create'),
    path('<int:course_id>/purchase/', views.CoursePurchaseCreateAPIView.as_view(), name='course-purchase'),
]
