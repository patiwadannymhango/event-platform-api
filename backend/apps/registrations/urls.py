from django.urls import path

from .views import (
    AdminRegistrationBulkUploadPreviewView,
    AdminRegistrationBulkUploadTemplateView,
    AdminRegistrationBulkUploadView,
    AdminRegistrationCreateView,
    AdminRegistrationDetailView,
    AdminRegistrationEditView,
    AdminRegistrationExportView,
    AdminRegistrationFilterOptionsView,
    AdminRegistrationListView,
    PublicRegistrationCreateView,
    PublicRegistrationFormView,
    PublicRegistrationLookupView,
)


urlpatterns = [

    path(
        "public/events/<uuid:event_id>/form/",
        PublicRegistrationFormView.as_view(),
        name="public-registration-form",
    ),

    path(
        "public/events/<uuid:event_id>/registrations/",
        PublicRegistrationCreateView.as_view(),
        name="public-registration-create",
    ),

    path(
        "public/lookup/",
        PublicRegistrationLookupView.as_view(),
        name="public-registration-lookup",
    ),

    # Admin
    path(
        "admin/events/<uuid:event_id>/registrations/",
        AdminRegistrationListView.as_view(),
        name="admin-registration-list",
    ),
    path(
        "admin/events/<uuid:event_id>/registrations/create/",
        AdminRegistrationCreateView.as_view(),
        name="admin-registration-create",
    ),
    path(
        "admin/events/<uuid:event_id>/registrations/bulk-upload/",
        AdminRegistrationBulkUploadView.as_view(),
        name="admin-registration-bulk-upload",
    ),
    path(
        "admin/events/<uuid:event_id>/registrations/bulk-upload/preview/",
        AdminRegistrationBulkUploadPreviewView.as_view(),
        name="admin-registration-bulk-upload-preview",
    ),
    path(
        "admin/events/<uuid:event_id>/registrations/bulk-upload/template/",
        AdminRegistrationBulkUploadTemplateView.as_view(),
        name="admin-registration-bulk-upload-template",
    ),
    path(
        "admin/events/<uuid:event_id>/registrations/export/",
        AdminRegistrationExportView.as_view(),
        name="admin-registration-export",
    ),
    path(
        "admin/events/<uuid:event_id>/registrations/filters/",
        AdminRegistrationFilterOptionsView.as_view(),
        name="admin-registration-filter-options",
    ),
    path(
        "admin/registrations/<uuid:pk>/",
        AdminRegistrationDetailView.as_view(),
        name="admin-registration-detail",
    ),
    path(
        "admin/registrations/<uuid:pk>/details/",
        AdminRegistrationEditView.as_view(),
        name="admin-registration-edit",
    ),
]