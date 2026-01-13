from rest_framework import serializers
from .models import Category, MenuItem

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category # Specify the model to be serialized
        fields = '__all__' # Include all fields of the model

class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem 
        fields = '__all__'