from django.urls import path

from modules.rspc.api import views as v

urlpatterns = [
    path(
        'proposals/',
        v.ResearchProposalView.as_view(),
        name='proposal-create',
    ),
    path(
        'proposals/mine/',
        v.ResearchProposalMineView.as_view(),
        name='proposal-mine',
    ),
    path(
        'proposals/queue/',
        v.ResearchProposalQueueView.as_view(),
        name='proposal-queue',
    ),
    path(
        'proposals/<int:proposal_id>/recommend/',
        v.ProposalDecisionView.as_view(),
        name='proposal-recommend',
    ),
    path(
        'proposals/<int:proposal_id>/verify/',
        v.ProposalVerifyView.as_view(),
        name='proposal-verify',
    ),
    path(
        'proposals/<int:proposal_id>/decide/',
        v.ProposalDecideView.as_view(),
        name='proposal-decide',
    ),
    path(
        'proposals/<int:proposal_id>/authorize/',
        v.ProposalAuthorizeView.as_view(),
        name='proposal-authorize',
    ),
]
