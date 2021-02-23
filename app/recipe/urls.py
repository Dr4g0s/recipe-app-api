from rest_framework.routers import DefaultRouter
from recipe import views
from django.urls import path, include


router = DefaultRouter()
router.register('tags', views.TagViewSet)

app_name = 'recipe'

urlpatterns = [
    path('', include(router.urls))
]
