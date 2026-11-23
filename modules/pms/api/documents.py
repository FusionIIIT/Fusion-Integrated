"""Documents and prior art (UC-PMS-004, 019)."""
from __future__ import annotations

from django.http import FileResponse
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from modules.pms.api import serializers as s
from modules.pms.api.common import PmsView, WriteView, found, gate, schema
from modules.pms.selectors import scoping
from modules.pms.services import documents, prior_art

DOC = {"id": 1, "kind": "specification", "title": "Complete specification",
       "sensitivity": "confidential",
       "versions": [{"id": 3, "number": 2, "original_name": "spec.pdf", "size_bytes": 182000,
                     "sha256": "9f2c...", "uploaded_at": "2026-11-02T10:00:00+05:30",
                     "uploaded_by_user_id": 1001, "is_current": True}]}
REFERENCE = {"id": 4, "application_id": 7, "kind": "patent", "title": "Graphene anode coating",
             "identifier": "US1234567B2", "url": "https://example.org/US1234567",
             "source_name": "Espacenet", "notes": "Closest art for claim 1.",
             "created_at": "2026-11-03T10:00:00+05:30"}


def _documents(actor, pk: int) -> Response:
    app = found(scoping.applications_for(actor).filter(pk=pk).first(), "application")
    rows = [{"id": doc.pk, "kind": doc.kind, "title": doc.title,
             "sensitivity": doc.sensitivity, "versions": versions}
            for doc, versions in scoping.documents_for(actor, app)]
    return Response(s.PmsDocumentSerializer(rows, many=True).data)


class DocumentsView(WriteView):
    parser_classes = [MultiPartParser]
    throttle_scope = "pms_upload"

    def get_permissions(self):
        code = "pms.document.view" if self.request.method == "GET" else "pms.document.create"
        return [p() for p in gate(code)]

    @schema("Documents you may read, each with its readable versions (BR-PMS-084)",
            response=s.PmsDocumentSerializer(many=True), example_out=[DOC])
    def get(self, request, pk: int):
        return _documents(self.actor, pk)

    @schema("Upload a PDF, or a new version of one (BR-PMS-014..016, 082)",
            request={"multipart/form-data": s.PmsUploadIn},
            response=s.PmsDocumentSerializer(many=True),
            status=201, example_out=[DOC])
    def post(self, request, pk: int):
        body = s.PmsUploadIn(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        documents.upload(actor=self.actor, pk=pk, uploaded=data["file"],
                         kind=data.get("kind", ""), title=data.get("title", ""),
                         sensitivity=data.get("sensitivity", ""),
                         document_id=data.get("document_id"))
        response = _documents(self.actor, pk)
        response.status_code = 201
        return response


class DownloadView(PmsView):
    permission_classes = gate("pms.document.view")

    @schema("Download one version, as an attachment", response=bytes)
    def get(self, request, pk: int):
        version, handle = documents.open_version(actor=self.actor, version_id=pk)
        response = FileResponse(handle, as_attachment=True, filename=version.original_name,
                                content_type="application/pdf")
        response["X-Content-Type-Options"] = "nosniff"
        return response


class SensitivityView(WriteView):
    permission_classes = gate("pms.document.update")

    @schema("Change a document's sensitivity (ruling C16)", request=s.PmsSensitivityIn,
            response=s.PmsDocumentRowSerializer, example_in={"sensitivity": "restricted"},
            example_out={"id": 1, "kind": "claims", "title": "Claims",
                         "sensitivity": "restricted", "updated_at": "2026-11-04T10:00:00+05:30"})
    def patch(self, request, pk: int):
        body = s.PmsSensitivityIn(data=request.data)
        body.is_valid(raise_exception=True)
        return Response(s.PmsDocumentRowSerializer(documents.set_sensitivity(
            actor=self.actor, document_id=pk, **body.validated_data)).data)


class SearchView(WriteView):
    permission_classes = gate("pms.prior_art.create")
    throttle_scope = "pms_search"

    @schema("Search recorded prior art and log the session (UC-PMS-004)", request=s.PmsSearchIn,
            response=dict, example_in={"query": "graphene anode coating",
                                       "classification_codes": ["H01M"]},
            example_out={"search_id": 12, "terms": ["graphene", "anode", "coating"],
                         "suggested_keywords": ["lithium"], "classification_codes": ["H01M"],
                         "suggested_classifications": ["H01M"],
                         "sources": [{"code": "patent_databases", "label": "Patent databases",
                                      "status": "not connected"}],
                         "results": [{"reference": REFERENCE, "score": 4}]})
    def post(self, request):
        body = s.PmsSearchIn(data=request.data)
        body.is_valid(raise_exception=True)
        out = prior_art.search(actor=self.actor, **body.validated_data)
        out["results"] = [{"reference": s.PmsPriorArtSerializer(r["reference"]).data,
                           "score": r["score"]} for r in out["results"]]
        return Response(out)


class ReferencesView(WriteView):
    def get_permissions(self):
        code = "pms.prior_art.view" if self.request.method == "GET" else "pms.prior_art.create"
        return [p() for p in gate(code)]

    @schema("Prior art attached to an application", response=s.PmsPriorArtSerializer(many=True),
            example_out=[REFERENCE])
    def get(self, request, pk: int):
        rows = scoping.prior_art_for(self.actor).filter(application_id=pk).order_by("-id")
        return Response(s.PmsPriorArtSerializer(rows, many=True).data)

    @schema("Attach a reference (PMS-AFR-146)", request=s.PmsReferenceIn,
            response=s.PmsPriorArtSerializer, status=201,
            example_in={"kind": "patent", "title": "Graphene anode coating",
                        "identifier": "US1234567B2"}, example_out=REFERENCE)
    def post(self, request, pk: int):
        body = s.PmsReferenceIn(data=request.data)
        body.is_valid(raise_exception=True)
        row = prior_art.attach(actor=self.actor, pk=pk, **body.validated_data)
        return Response(s.PmsPriorArtSerializer(row).data, status=201)
