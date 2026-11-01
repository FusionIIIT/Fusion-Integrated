from django.urls import path, include
from .views import ResearchProposalView, ResearchProposalMineView, ResearchProposalQueueView, ProposalDecisionView, ProposalVerifyView, ProposalDecideView, ProposalAuthorizeView

urlpatterns = [
    path('proposals/', ResearchProposalView.as_view(), name='proposal-create'),
    path('proposals/mine/', ResearchProposalMineView.as_view(), name='proposal-mine'),
    path('proposals/queue/', ResearchProposalQueueView.as_view(), name='proposal-queue'),
    path('proposals/<int:proposal_id>/recommend/', ProposalDecisionView.as_view(), name='proposal-recommend'),
    path('proposals/<int:proposal_id>/verify/', ProposalVerifyView.as_view(), name='proposal-verify'),
    path('proposals/<int:proposal_id>/decide/', ProposalDecideView.as_view(), name='proposal-decide'),
    path('proposals/<int:proposal_id>/authorize/', ProposalAuthorizeView.as_view(), name='proposal-authorize'),
]
