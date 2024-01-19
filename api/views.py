from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from rest_framework.response import Response
from .models import Category, MenuItem, Cart, Order, OrderItem
from . import serializers

def check_not_get(self):
    permission_classes = []
    if self.request.method != 'GET':
        permission_classes.append(IsAuthenticated)
    return [permission() for permission in permission_classes]

class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer

    def get_permissions(self):
        return check_not_get(self)

class SingleCategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer

class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = serializers.MenuItemSerializer
    search_fields = ['category__title']
    ordering_fields = ['price']

    def get_permissions(self):
        return check_not_get(self)
    
class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = serializers.MenuItemSerializer

    def get_permissions(self):
        return check_not_get(self)
    
class CartView(generics.ListCreateAPIView):
    queryset = Cart.objects.all()
    serializer_class = serializers.CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user = self.request.user)

    def delete(self, request, *args, **kwargs):
        Cart.objects.filter(user = request.user).delete()
        return Response('ok')

class OrderView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = serializers.OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.groups.count() == 0: # type: ignore
            return Order.objects.filter(user = self.request.user)
        elif self.request.user.groups.filter(name = 'delivery_crew').exists(): # type: ignore
            return Order.objects.filter(delivery_crew = self.request.user)
        else:
            return Order.objects.all()

    def create(self, request, *args, **kwargs):
        menuitem_count = Cart.objects.filter(user = request.user).count()
        if menuitem_count == 0:
            return Response({"message":'Cart is empty'})
        data = request.data.copy()
        total = self.get_total_price(request.user)
        data['total'] = total
        data['user'] = request.user.id
        
        order_serializer = serializers.OrderSerializer(data = data)
        
        if order_serializer.is_valid(raise_exception=True):
            print('valid')
            order = order_serializer.save()

            items = Cart.objects.all().filter(user=self.request.user).all()
            for item in items.values():
                orderitem = OrderItem(
                    order=order,
                    menuitem_id=item['menuitem_id'],
                    price=item['price'],
                    quantity=item['quantity'],
                )
                orderitem.save()
            Cart.objects.all().filter(user=self.request.user).delete()
            return Response(order_serializer.data)
        #return Response({"message":'Invalid Input'}, status=400)
    def get_total_price(self, user):
        total = 0
        items = Cart.objects.all().filter(user=user).all()
        for item in items.values():
            total += item['price']
        return total
    
class SingleOrderView(generics.RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = serializers.OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        if self.request.user.groups.count() == 0: # type: ignore
            return Response({"message":'Not authorized'}, status=403)
        else:
            return super().update(request, *args, **kwargs)