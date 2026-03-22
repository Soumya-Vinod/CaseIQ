from django.urls import path
from . import views

urlpatterns = [
    path('query/', views.process_legal_query, name='legal-query'),
    path('query/history/', views.query_history, name='query-history'),
    path('query/<uuid:query_id>/', views.get_query_detail, name='query-detail'),
    path('sections/', views.BNSSSectionListView.as_view(), name='bnss-sections'),
]