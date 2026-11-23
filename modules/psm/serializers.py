from rest_framework import serializers
from .models import StockItem, PurchaseIndent, IndentItem

class StockItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class PurchaseIndentSerializer(serializers.ModelSerializer):
    status = serializers.CharField(default='draft', required=False)

    class Meta:
        model = PurchaseIndent
        fields = '__all__'
        read_only_fields = ['id', 'user_id', 'created_at', 'updated_at']

class IndentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndentItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
