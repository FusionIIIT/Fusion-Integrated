class Feature1ListView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("elm"),
                          HasAnyPermission("elm.feature1.view")]
    filterset_class = Feature1Filter

    def get_queryset(self):
        return selectors.visible_feature1s(self.request.principal)   # never Feature1.objects

    def get_serializer_class(self):
        return WriteFeature1Serializer if self.request.method == "POST" else ReadFeature1Serializer

    @extend_schema(summary="List feature 1s visible to the caller", tags=["elm"],
                   examples=[OpenApiExample("open feature 1", value={...})])
    def get(self, *a, **kw):
        return super().get(*a, **kw)
```

tests/test_feature1.py
