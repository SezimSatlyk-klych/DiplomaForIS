from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('password-reset/request/', views.PasswordResetRequestAPIView.as_view(), name='password-reset-request'),
    path('password-reset/verify/', views.PasswordResetVerifyAPIView.as_view(), name='password-reset-verify'),
    path('password-reset/confirm/', views.PasswordResetConfirmAPIView.as_view(), name='password-reset-confirm'),
    path('profile/', views.ProfileAPIView.as_view(), name='profile'),
    path('specialist/', views.SpecialistAPIView.as_view(), name='specialist'),
    path('specialist/dashboard/', views.SpecialistDashboardAPIView.as_view(), name='specialist-dashboard'),
    path('specialist/description/', views.SpecialistDescriptionAPIView.as_view(), name='specialist-description'),
    path('specialist/description/choices/', views.SpecialistDescriptionChoicesAPIView.as_view(), name='specialist-description-choices'),
    path('children/choices/', views.ChildChoicesAPIView.as_view(), name='child-choices'),
    path('children/', views.ChildListCreateAPIView.as_view(), name='child-list'),
    path('children/<int:pk>/', views.ChildDetailAPIView.as_view(), name='child-detail'),
    path('settings/profile/', views.ParentSettingsProfileAPIView.as_view(), name='parent-settings-profile'),
    path('settings/child/', views.ParentSettingsChildAPIView.as_view(), name='parent-settings-child'),
    path('settings/specialist/', views.SpecialistSettingsProfileAPIView.as_view(), name='specialist-settings-profile'),
    path('settings/address/', views.ParentSettingsAddressAPIView.as_view(), name='parent-settings-address'),
    path('settings/change-password/', views.ChangePasswordAPIView.as_view(), name='settings-change-password'),
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
