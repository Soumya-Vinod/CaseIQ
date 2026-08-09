from django.urls import path
from . import views

urlpatterns = [
    path('query/', views.process_legal_query, name='legal-query'),
    path('query/history/', views.QueryHistoryView.as_view(), name='query-history'),
    path('query/<uuid:id>/', views.QueryDetailView.as_view(), name='query-detail'),
    path('sections/', views.BNSSSectionListView.as_view(), name='sections-list'),
    path('timeline/', views.generate_legal_timeline, name='legal-timeline'),
    path('rights-card/', views.generate_rights_card, name='rights-card'),
    path('simulate/', views.simulate_scenario, name='scenario-simulate'),
    path('verify-citation/', views.verify_citation, name='verify-citation'),
]