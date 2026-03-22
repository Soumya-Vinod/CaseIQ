from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.LegalCategoryListView.as_view(), name='categories'),
    path('provisions/', views.LegalProvisionListView.as_view(), name='provisions'),
    path('rights/', views.CitizenRightListView.as_view(), name='rights'),
    path('search/', views.semantic_search, name='semantic-search'),
]
