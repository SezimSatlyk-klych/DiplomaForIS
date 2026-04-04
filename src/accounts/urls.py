from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView

from . import views

urlpatterns = [
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('profile/', views.ProfileAPIView.as_view(), name='profile'),
    path('specialist/', views.SpecialistAPIView.as_view(), name='specialist'),
    path('specialist/dashboard/', views.SpecialistDashboardAPIView.as_view(), name='specialist-dashboard'),
    path('specialist/description/', views.SpecialistDescriptionAPIView.as_view(), name='specialist-description'),
    path('specialist/description/choices/', views.SpecialistDescriptionChoicesAPIView.as_view(), name='specialist-description-choices'),
    path('children/choices/', views.ChildChoicesAPIView.as_view(), name='child-choices'),
    path('children/', views.ChildListCreateAPIView.as_view(), name='child-list'),
    path('children/<int:pk>/', views.ChildDetailAPIView.as_view(), name='child-detail'),
    path('public/specialists/cards/', views.PublicSpecialistCardsListAPIView.as_view(), name='specialist-public-cards'),
    path(
        'public/specialists/cards/<int:specialist_id>/courses/',
        views.PublicSpecialistCoursesListAPIView.as_view(),
        name='specialist-public-courses',
    ),
    path(
        'public/specialists/cards/<int:specialist_id>/',
        views.PublicSpecialistCardRetrieveAPIView.as_view(),
        name='specialist-public-card-detail',
    ),
]
