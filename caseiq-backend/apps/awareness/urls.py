from django.urls import path
from . import views

urlpatterns = [
    path('news/', views.LegalNewsFeedView.as_view(), name='news-feed'),
    path('news/fetch/', views.fetch_news, name='news-fetch'),
    path('news/<uuid:news_id>/', views.news_detail, name='news-detail'),
    path('education/', views.EducationalContentView.as_view(), name='education-list'),
    path('education/<uuid:content_id>/', views.educational_detail, name='education-detail'),
    path('education/create/', views.create_educational_content, name='education-create'),
]