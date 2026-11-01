from rest_framework import serializers
from modules.hostel.models import Hostel, WardenRoleBinding, CaretakerRoleBinding

class HostelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = '__all__'

class WardenRoleBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WardenRoleBinding
        fields = '__all__'

class CaretakerRoleBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaretakerRoleBinding
        fields = '__all__'
