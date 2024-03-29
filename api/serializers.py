from rest_framework import serializers
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from .models import Category, MenuItem, Cart, Order, OrderItem

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug']
        

class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.StringRelatedField(source='category')
    category = serializers.PrimaryKeyRelatedField(queryset = Category.objects.all())
    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'category', 'featured', 'category_name','description']
        extra_kwargs = {
            "category_name": {"read_only": True}
        }

class CartSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset = User.objects.all(), default=serializers.CurrentUserDefault())
    menuitem = serializers.PrimaryKeyRelatedField(queryset = MenuItem.objects.all())

    def validate(self, attrs):
        quantity = attrs.get('quantity')
        menuitem = attrs.get('menuitem')
        if quantity < 1:
            raise serializers.ValidationError("Quantity must be greater than 0")
        
        attrs['unit_price'] = menuitem.price
        attrs['price'] = Decimal(menuitem.price) * Decimal(quantity)

        return attrs
    
    class Meta:
        model = Cart
        fields = ['id','user', 'menuitem', 'unit_price', 'quantity', 'price']
        extra_kwargs = {
            'price': {'read_only': True},
            'unit_price': {'read_only': True},
        }

class CartUserSerializer(serializers.ModelSerializer):
    menuitem = serializers.PrimaryKeyRelatedField(queryset = MenuItem.objects.all())
    menuitem_name = serializers.SerializerMethodField()
    class Meta:
        model = Cart
        fields = ['id', 'menuitem', 'quantity', 'price', 'unit_price', 'menuitem_name']
    
    def get_menuitem_name(self, obj):
        return obj.menuitem.title

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['order', 'menuitem', 'quantity', 'price']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class OrderUpdateSerializer(serializers.ModelSerializer):
    orderitem = OrderItemSerializer(many=True, read_only=True, source='order')
    delivery_crew = UserSerializer()
    class Meta:
        model = Order
        fields = ['id', 'user', 'delivery_crew', 'status', 'date', 'total', 'orderitem']

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True, source='order')
    delivery_crew = UserSerializer(read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'user', 'delivery_crew', 'status', 'date', 'total', 'order_items']

