from django.urls import path

from modules.placement.api import academics as a
from modules.placement.api import documents as d
from modules.placement.api import views as v

urlpatterns = [
    # postings
    path("postings", v.PostingListView.as_view(), name="placement-postings"),
    path("postings/<int:pk>", v.PostingDetailView.as_view(),
         name="placement-posting"),
    path("postings/<int:pk>/publish", v.PostingPublishView.as_view(),
         name="placement-posting-publish"),
    path("postings/<int:pk>/eligibility", v.PostingEligibilityView.as_view(),
         name="placement-posting-eligibility"),

    # applications
    path("applications", v.ApplicationListView.as_view(),
         name="placement-applications"),
    path("applications/apply", v.ApplyView.as_view(), name="placement-apply"),
    path("applications/<int:pk>/transition", v.ApplicationTransitionView.as_view(),
         name="placement-application-transition"),

    # documents
    path("documents", d.MyDocumentsView.as_view(), name="placement-documents"),
    path("documents/<int:pk>", d.MyDocumentDetailView.as_view(),
         name="placement-document"),
    path("documents/<int:pk>/download", d.DocumentDownloadView.as_view(),
         name="placement-document-download"),

    # profile
    path("profile", v.MyProfileView.as_view(), name="placement-my-profile"),
    path("profile/resume", v.MyResumeView.as_view(), name="placement-my-resume"),
    path("profiles/<int:user_id>", v.ProfileDetailView.as_view(),
         name="placement-profile"),

    # companies
    path("companies", v.CompanyListView.as_view(), name="placement-companies"),
    path("companies/<int:pk>/<str:action>", v.CompanyApprovalView.as_view(),
         name="placement-company-approval"),

    # interviews
    path("interviews/rounds", v.InterviewRoundListView.as_view(),
         name="placement-rounds"),
    path("interviews/rounds/<int:pk>/candidates", v.RoundCandidatesView.as_view(),
         name="placement-round-candidates"),
    path("interviews/rounds/<int:pk>/outcome", v.RoundOutcomeView.as_view(),
         name="placement-round-outcome"),

    # offers
    path("offers", v.OfferListView.as_view(), name="placement-offers"),
    path("offers/issue", v.OfferIssueView.as_view(), name="placement-offer-issue"),
    path("offers/<int:pk>/respond", v.OfferRespondView.as_view(),
         name="placement-offer-respond"),

    # announcements
    path("announcements", v.AnnouncementListView.as_view(),
         name="placement-announcements"),
    path("announcements/<int:pk>/withdraw", v.AnnouncementWithdrawView.as_view(),
         name="placement-announcement-withdraw"),

    # CPI directory — the whole cohort's declared standing, staff only
    path("students/cpi", a.AcademicDirectoryView.as_view(),
         name="placement-cpi-directory"),
    path("students/cpi/filters", a.AcademicFiltersView.as_view(),
         name="placement-cpi-filters"),

    # statistics
    path("stats", v.StatsView.as_view(), name="placement-stats"),

    # recruiter portal
    path("recruiters/invite", v.RecruiterInviteView.as_view(),
         name="placement-recruiter-invite"),
    path("recruiters/accept", v.RecruiterAcceptView.as_view(),
         name="placement-recruiter-accept"),
    path("recruiters/login", v.RecruiterLoginView.as_view(),
         name="placement-recruiter-login"),
    path("recruiters/logout", v.RecruiterLogoutView.as_view(),
         name="placement-recruiter-logout"),
    path("recruiters/me", v.RecruiterMeView.as_view(),
         name="placement-recruiter-me"),
]
