from django.urls import path

from . import views


urlpatterns = [
    path('choices/', views.CourseChoicesAPIView.as_view(), name='course-choices'),
    path('public/cards/', views.PublicCourseCardsListAPIView.as_view(), name='course-public-cards'),
    path('public/cards/<int:course_id>/', views.PublicCourseCardRetrieveAPIView.as_view(), name='course-public-card-detail'),
    path('public/cards/<int:course_id>/description/', views.PublicCourseDescriptionAPIView.as_view(), name='course-public-description'),
    path('public/cards/<int:course_id>/content/', views.PublicCourseContentAPIView.as_view(), name='course-public-content'),
    path('public/cards/<int:course_id>/specialist/', views.PublicCourseSpecialistAPIView.as_view(), name='course-public-specialist'),
    path('public/previews/', views.PublicCoursePreviewListAPIView.as_view(), name='course-public-previews'),
    path('', views.CourseListCreateAPIView.as_view(), name='course-list-create'),
    path('<int:pk>/', views.CourseRetrieveUpdateDestroyAPIView.as_view(), name='course-detail'),
    path('<int:pk>/description/', views.SpecialistCourseDescriptionAPIView.as_view(), name='course-description'),
    path('<int:pk>/content/', views.SpecialistCourseContentAPIView.as_view(), name='course-content'),
    path('<int:pk>/specialist/', views.SpecialistCourseSpecialistAPIView.as_view(), name='course-specialist'),
    path('<int:course_id>/modules/', views.CourseModuleListCreateAPIView.as_view(), name='coursemodule-list-create'),
    path(
        '<int:course_id>/modules/<int:pk>/',
        views.CourseModuleRetrieveUpdateDestroyAPIView.as_view(),
        name='coursemodule-detail',
    ),
    path('<int:course_id>/reviews/', views.CourseReviewListCreateAPIView.as_view(), name='course-review-list-create'),
    path('<int:course_id>/purchase/', views.CoursePurchaseCreateAPIView.as_view(), name='course-purchase'),
]
