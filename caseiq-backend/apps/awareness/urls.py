from django.urls import path
from . import views

urlpatterns = [
    path('news/', views.LegalNewsListView.as_view(), name='news-list'),
    path('news/fetch/', views.fetch_news, name='news-fetch'),
    path('news/<uuid:id>/', views.LegalNewsDetailView.as_view(), name='news-detail'),
    path('education/', views.EducationalContentListView.as_view(), name='education-list'),
    path('education/create/', views.create_educational_content, name='education-create'),
    path('education/<uuid:id>/', views.EducationalContentDetailView.as_view(), name='education-detail'),
]