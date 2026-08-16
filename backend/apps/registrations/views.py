from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    RetrieveAPIView,
)

from rest_framework.permissions import (
    AllowAny,
)

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.models import Event

from .models import Registration
from .serializers import (
    PublicRegistrationSerializer,
    RegistrationFormSerializer,
)
from .services import create_registration


class PublicRegistrationFormView(
    RetrieveAPIView
):

    permission_classes = [
        AllowAny,
    ]

    serializer_class = (
        RegistrationFormSerializer
    )

    lookup_url_kwarg = "event_id"

    def get_object(self):

        event = Event.objects.get(
            id=self.kwargs["event_id"],
            is_active=True,
        )

        return event.registration_form


class PublicRegistrationCreateView(
    APIView
):

    permission_classes = [
        AllowAny,
    ]

    def post(
        self,
        request,
        event_id,
    ):

        try:

            event = Event.objects.get(
                id=event_id,
                is_active=True,
            )

        except Event.DoesNotExist:

            return Response(
                {
                    "detail": (
                        "Event not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = (
            PublicRegistrationSerializer(
                data=request.data,
                context={
                    "event": event,
                },
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        registration = (
            create_registration(
                event=event,
                category=serializer.validated_data[
                    "category"
                ],
                participant_data=(
                    serializer.validated_data[
                        "participant"
                    ]
                ),
                form_data=(
                    serializer.validated_data[
                        "form_data"
                    ]
                ),
                reserve=serializer.validated_data.get(
                    "reserve", False
                ),
            )
        )

        return Response(
            {
                "registration": {
                    "id": registration.id,
                    "registration_number": (
                        registration
                        .registration_number
                    ),
                    "status": (
                        registration.status
                    ),
                    "amount": str(
                        registration.amount
                    ),
                    "currency": (
                        registration.currency
                    ),
                }
            },
            status=status.HTTP_201_CREATED,
        )


class PublicRegistrationLookupView(APIView):
    """
    GET /api/v1/registrations/public/lookup/?q=<reference-or-email>

    Powers the "track your registration" feature on the public site.
    Deliberately returns a small, non-sensitive subset of fields.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()

        if not query:
            return Response(
                {"detail": "Provide a reference number or email as ?q="},
                status=status.HTTP_400_BAD_REQUEST,
            )

        registration = (
            Registration.objects
            .select_related("participant", "category")
            .filter(registration_number__iexact=query)
            .first()
            or Registration.objects
            .select_related("participant", "category")
            .filter(participant__email__iexact=query)
            .order_by("-registered_at")
            .first()
        )

        if not registration:
            return Response(
                {"detail": "No matching registration found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "reference": registration.registration_number,
                "status": registration.status,
                "category": registration.category.name,
                "amount": str(registration.amount),
                "currency": registration.currency,
                "full_name": (
                    f"{registration.participant.first_name} "
                    f"{registration.participant.last_name}"
                ).strip(),
                "submitted_at": registration.registered_at,
            }
        )

# ---------------------------------------------------------------------------
# Admin-facing views
# ---------------------------------------------------------------------------

import csv
import io

import openpyxl
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from django.utils.dateparse import parse_datetime

from rest_framework import filters
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.common.access import (
    EVENT_REGISTRATION_MANAGE_ROLES,
    EVENT_VIEW_ROLES,
    require_event_role,
)
from apps.common.permissions import HasEventRole

from .models import RegistrationCategory
from .serializers import (
    AdminManualRegistrationSerializer,
    AdminRegistrationSerializer,
    AdminRegistrationStatusUpdateSerializer,
)
from .services import create_registration, generate_registration_number


class AdminRegistrationListView(ListAPIView):
    """
    GET /api/v1/registrations/admin/events/<event_id>/registrations/

    Supports ?status=, ?category=, ?search=, ?ordering= and standard
    pagination — this is the data source for the admin registrations
    table. ?gender=, ?organisation=, ?attendance_type= filter on the
    equivalent keys inside form_data (there's no dedicated column for
    these — the registration form is admin-configurable per event, so
    these answers live in the JSON blob rather than fixed model fields).
    """

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_VIEW_ROLES)]
    serializer_class = AdminRegistrationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "category"]
    search_fields = [
        "registration_number",
        "participant__first_name",
        "participant__last_name",
        "participant__email",
        "participant__phone",
    ]
    ordering_fields = ["registered_at", "amount", "status"]

    def get_queryset(self):
        qs = (
            Registration.objects
            .select_related("participant", "category", "event")
            .filter(event_id=self.kwargs["event_id"])
        )

        gender = self.request.query_params.get("gender")
        if gender:
            qs = qs.filter(form_data__gender=gender)

        organisation = self.request.query_params.get("organisation")
        if organisation:
            qs = qs.filter(form_data__club_or_institution=organisation)

        attendance_type = self.request.query_params.get("attendance_type")
        if attendance_type:
            qs = qs.filter(form_data__attendance_type=attendance_type)

        return qs


class AdminRegistrationFilterOptionsView(APIView):
    """
    GET /api/v1/registrations/admin/events/<event_id>/registrations/filters/

    Distinct values for the admin table's filter dropdowns — genders/
    organisations/attendance types come from form_data (see
    AdminRegistrationListView), so they can't be hardcoded; categories are
    event-specific too. Small and cheap enough to just compute directly
    rather than caching.
    """

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_VIEW_ROLES)]

    def get(self, request, event_id):
        qs = Registration.objects.filter(event_id=event_id)

        def distinct(key):
            values = qs.values_list(f"form_data__{key}", flat=True).distinct()
            return sorted({v for v in values if v})

        categories = list(
            RegistrationCategory.objects
            .filter(event_id=event_id)
            .values("id", "name")
            .order_by("name")
        )

        return Response(
            {
                "categories": categories,
                "genders": distinct("gender"),
                "organisations": distinct("club_or_institution"),
                "attendance_types": distinct("attendance_type"),
            }
        )


class AdminRegistrationDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/v1/registrations/admin/registrations/<id>/

    PATCH only accepts {"status": "..."} — use this to flip a
    registration from RESERVED/PENDING_PAYMENT to CONFIRMED once a
    manual/cash payment has been taken, or to CANCELLED/REFUNDED.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AdminRegistrationSerializer
    queryset = Registration.objects.select_related("participant", "category", "event")

    def get_object(self):
        # Not keyed by event_id in the URL (it's looked up by
        # registration id), so the role check happens here once the
        # event is known, rather than via a HasEventRole permission
        # class. GET only needs view access; PATCH/DELETE (both of which
        # call this via the generic dispatch) need registration-manage
        # access.
        registration = super().get_object()

        required_roles = (
            EVENT_VIEW_ROLES
            if self.request.method == "GET"
            else EVENT_REGISTRATION_MANAGE_ROLES
        )

        require_event_role(
            self.request.user,
            registration.event_id,
            *required_roles,
        )

        return registration

    def patch(self, request, *args, **kwargs):
        registration = self.get_object()

        serializer = AdminRegistrationStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        old_status = registration.status

        registration.status = new_status
        registration.save(update_fields=["status", "updated_at"])

        # Manually marking something CONFIRMED (e.g. cash paid at the
        # door) should notify the runner just like an online payment
        # would, but only if we're actually transitioning INTO confirmed.
        if new_status == Registration.Status.CONFIRMED and old_status != new_status:
            from apps.notifications.services import notify_payment_confirmed
            notify_payment_confirmed(registration)

        return Response(AdminRegistrationSerializer(registration).data)


class AdminRegistrationCreateView(APIView):
    """
    POST /api/v1/registrations/admin/events/<event_id>/registrations/

    Manual "register a participant" — used by the admin for walk-ins,
    phone registrations, etc. Defaults to CONFIRMED status (cash taken in
    person) but the admin can pick any status.
    """

    permission_classes = [
        IsAuthenticated,
        HasEventRole(*EVENT_REGISTRATION_MANAGE_ROLES),
    ]

    def post(self, request, event_id):
        event = Event.objects.get(id=event_id)

        serializer = AdminManualRegistrationSerializer(
            data=request.data, context={"event": event}
        )
        serializer.is_valid(raise_exception=True)

        category = serializer.validated_data["category_id"]

        registration = create_registration(
            event=event,
            category=category,
            participant_data=serializer.validated_data["participant"],
            form_data=serializer.validated_data.get("form_data", {}),
            reserve=False,
        )

        desired_status = serializer.validated_data["status"]
        if desired_status != registration.status:
            registration.status = desired_status
            registration.save(update_fields=["status", "updated_at"])

        return Response(
            AdminRegistrationSerializer(registration).data,
            status=status.HTTP_201_CREATED,
        )


class AdminRegistrationBulkUploadView(APIView):
    """
    POST /api/v1/registrations/admin/events/<event_id>/registrations/bulk-upload/

    Accepts a CSV or XLSX file (multipart field name "file") with columns:
    first_name, last_name, email, phone, category_code, status (optional,
    defaults to CONFIRMED).

    Returns a report of created rows and any rows that failed, rather
    than failing the whole batch on one bad row.
    """

    permission_classes = [
        IsAuthenticated,
        HasEventRole(*EVENT_REGISTRATION_MANAGE_ROLES),
    ]
    parser_classes = [MultiPartParser]

    REQUIRED_COLUMNS = ["first_name", "last_name", "category_code"]

    def post(self, request, event_id):
        event = Event.objects.get(id=event_id)
        upload = request.FILES.get("file")

        if not upload:
            return Response(
                {"detail": "Attach a file under the 'file' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rows = self._parse_rows(upload)

        categories = {
            c.code: c
            for c in RegistrationCategory.objects.filter(event=event)
        }

        created = []
        errors = []

        for index, row in enumerate(rows, start=2):  # header is row 1

            missing = [c for c in self.REQUIRED_COLUMNS if not row.get(c)]
            if missing:
                errors.append({"row": index, "error": f"Missing: {', '.join(missing)}"})
                continue

            category = categories.get(row["category_code"])
            if not category:
                errors.append(
                    {"row": index, "error": f"Unknown category_code '{row['category_code']}'"}
                )
                continue

            try:
                registration = create_registration(
                    event=event,
                    category=category,
                    participant_data={
                        "first_name": row["first_name"],
                        "last_name": row["last_name"],
                        "email": row.get("email", ""),
                        "phone": row.get("phone", ""),
                    },
                    form_data={},
                    reserve=False,
                )

                desired_status = (row.get("status") or "CONFIRMED").upper()
                if desired_status in Registration.Status.values and desired_status != registration.status:
                    registration.status = desired_status
                    registration.save(update_fields=["status", "updated_at"])

                created.append(registration.registration_number)

            except Exception as exc:  # noqa: BLE001
                errors.append({"row": index, "error": str(exc)})

        return Response(
            {
                "created_count": len(created),
                "created_references": created,
                "error_count": len(errors),
                "errors": errors,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST,
        )

    def _parse_rows(self, upload):
        filename = (upload.name or "").lower()

        if filename.endswith(".csv"):
            text = upload.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            return [
                {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
                for row in reader
            ]

        # Assume Excel otherwise
        workbook = openpyxl.load_workbook(upload, data_only=True)
        sheet = workbook.active

        rows_iter = sheet.iter_rows(values_only=True)
        headers = [str(h or "").strip().lower() for h in next(rows_iter)]

        rows = []
        for values in rows_iter:
            if all(v in (None, "") for v in values):
                continue
            row = {
                headers[i]: ("" if v is None else str(v).strip())
                for i, v in enumerate(values)
                if i < len(headers)
            }
            rows.append(row)

        return rows


class AdminRegistrationExportView(APIView):
    """
    GET /api/v1/registrations/admin/events/<event_id>/registrations/export/

    Streams an .xlsx of every registration for the event — this is what
    the admin's "Export to Excel" button hits directly (it's a normal
    GET, so the frontend can just set window.location or an <a href>).
    """

    permission_classes = [IsAuthenticated, HasEventRole(*EVENT_VIEW_ROLES)]

    COLUMNS = [
        ("Reference", lambda r: r.registration_number),
        ("Status", lambda r: r.get_status_display()),
        ("First name", lambda r: r.participant.first_name),
        ("Last name", lambda r: r.participant.last_name),
        ("Email", lambda r: r.participant.email),
        ("Phone", lambda r: r.participant.phone),
        ("Gender", lambda r: r.form_data.get("gender", "")),
        ("Age range", lambda r: r.form_data.get("age_range", "")),
        ("Country", lambda r: r.form_data.get("country", "")),
        ("T-shirt size", lambda r: r.form_data.get("tshirt_size", "")),
        ("Category", lambda r: r.category.name),
        ("Attendance", lambda r: r.form_data.get("attendance_type", "")),
        ("Organisation", lambda r: r.form_data.get("club_or_institution", "")),
        ("Emergency contact name", lambda r: r.form_data.get("emergency_contact_name", "")),
        ("Emergency contact phone", lambda r: r.form_data.get("emergency_contact_phone", "")),
        ("Medical notes", lambda r: r.form_data.get("medical_notes", "")),
        ("Amount", lambda r: float(r.amount)),
        ("Currency", lambda r: r.currency),
        ("Registered at", lambda r: r.registered_at.replace(tzinfo=None) if r.registered_at else None),
    ]

    def get(self, request, event_id):
        event = Event.objects.get(id=event_id)

        registrations = (
            Registration.objects
            .select_related("participant", "category")
            .filter(event=event)
            .order_by("-registered_at")
        )

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Registrations"

        for col_index, (header, _) in enumerate(self.COLUMNS, start=1):
            sheet.cell(row=1, column=col_index, value=header)

        for row_index, registration in enumerate(registrations, start=2):
            for col_index, (_, getter) in enumerate(self.COLUMNS, start=1):
                sheet.cell(row=row_index, column=col_index, value=getter(registration))

        for col_index in range(1, len(self.COLUMNS) + 1):
            sheet.column_dimensions[get_column_letter(col_index)].width = 22

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{event.slug}-registrations.xlsx"'
        )
        return response
