from django.urls import path

from . import views


urlpatterns = [
    path("medicines/search", views.medicine_search, name="medicine-search"),
    path("medicines/<int:pk>/prices", views.medicine_prices, name="medicine-prices"),
    path("medicines/<int:pk>/", views.medicine_detail, name="medicine-detail"),
    path("tests/search", views.test_search, name="test-search"),
    path("tests/<int:pk>/prices", views.test_prices, name="test-prices"),
    path("estimate", views.estimate, name="estimate"),
]
