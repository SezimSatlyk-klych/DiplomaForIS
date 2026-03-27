from django.urls import path

from . import views


urlpatterns = [
    path('mood-trackings/choices/', views.MoodTrackingChoicesAPIView.as_view(), name='mood-tracking-choices'),
    path('mood-trackings/', views.MoodTrackingListCreateAPIView.as_view(), name='mood-tracking-list-create'),
    path('mood-trackings/<int:pk>/', views.MoodTrackingRetrieveUpdateDestroyAPIView.as_view(), name='mood-tracking-detail'),
    path('mood-trackings/summary/', views.MoodTrackingSummaryAPIView.as_view(), name='mood-tracking-summary'),
]
