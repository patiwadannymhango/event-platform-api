from django.urls import path

from .views import (
    OrganizationDetailView,
    OrganizationListView,
)

urlpatterns = [

    path(
        "",
        OrganizationListView.as_view(),
        name="organization-list",
    ),

    path(
        "<uuid:organization_id>/",
        OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
]