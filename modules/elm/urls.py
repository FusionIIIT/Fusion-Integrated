
from django.urls import path

from .views import MyLeavesView, SubstituteQueueView, SubstituteRespondView, UnitHeadApprovalsView      



urlpatterns = [

    path('my-leaves/', MyLeavesView.as_view(), name='my-leaves'),

    path('substitute-queue/', SubstituteQueueView.as_view(), name='substitute-queue'),

    path('substitute-respond/<int:pk>/', SubstituteRespondView.as_view(), name='substitute-respond'),   

    path('unit-head-approvals/', UnitHeadApprovalsView.as_view(), name='unit-head-approvals'),

]
