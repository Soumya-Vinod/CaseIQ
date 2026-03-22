from django.urls import path
from . import views

urlpatterns = [
    path('draft/', views.generate_complaint_draft, name='complaint-draft'),
    path('history/', views.complaint_history, name='complaint-history'),
    path('<uuid:complaint_id>/', views.complaint_detail, name='complaint-detail'),
    path('<uuid:complaint_id>/download/', views.download_complaint_pdf, name='complaint-download'),
]