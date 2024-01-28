from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import generics, viewsets
from rest_framework.response import Response
from .models import Category, MenuItem, Cart, Order, OrderItem
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
from . import serializers

def check_edit_permission(self):
    permission_classes = []
    if self.request.method != 'GET':
        permission_classes.append(IsAuthenticated)
    return [permission() for permission in permission_classes]

class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer

    def get_permissions(self):
        return check_edit_permission(self)

class SingleCategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer

class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = serializers.MenuItemSerializer
    search_fields = ['category__title']
    ordering_fields = ['price']

    def get_permissions(self):
        return check_edit_permission(self)
    
class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = serializers.MenuItemSerializer

    def get_permissions(self):
        return check_edit_permission(self)
    
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
        
    def get_total_price(self, user):
        total = 0
        items = Cart.objects.all().filter(user=user).all()
        for item in items.values():
            total += item['price']
        return total
    
class SingleOrderView(generics.RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = serializers.OrderUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        if request.user.groups.count() == 0:
            return Response({"message": "Not Authorized"})
        
        instance = self.get_object()
        if request.user.groups.filter(name="delivery_crew").exists():
            state = request.data.get("status")
            if state is not None:
                instance.status = state
                instance.save()
                return Response({"message": "Order status updated"})
            else:
                return Response({"message": "Status not provided"})
        elif request.user.groups.filter(name="manager").exists():
            delivery_crew_id = request.data.get('delivery_crew')
            state = request.data.get("status")
            if delivery_crew_id is not None:
                delivery_crew = User.objects.get(id=delivery_crew_id)
                instance.delivery_crew = delivery_crew
            if state is not None:
                instance.status = state

            instance.save()
            return Response({"message": "Order updated"})
        else:
            return Response({"message": "Not Authorized"})
            
class ManagerViewSet(viewsets.ViewSet): 
    permission_classes = [IsAdminUser]
    def list(self, request):
        user = User.objects.all().filter(groups__name='manager')
        items = serializers.UserSerializer(user, many=True)
        return Response(items.data)
    
    def create(self, request):
        user = get_object_or_404(User, username=request.data['username'])
        managers = Group.objects.get(name="Manager")
        managers.user_set.add(user) # type: ignore 
        return Response({"message": "user added to the manager group"}, 200)
    
    def destroy(self, request):
        user = get_object_or_404(User, username=request.data['username'])
        managers = Group.objects.get(name="Manager")
        managers.user_set.remove(user) # type: ignore
        return Response({"message": "user removed from the manager group"}, 200)
    
class DeliveryCrewViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    def list(self, request):
        users = User.objects.all().filter(groups__name='Delivery Crew')
        items = serializers.UserSerializer(users, many=True)
        return Response(items.data)

    def create(self, request):
        #only for super admin and managers
        if self.request.user.is_superuser == False: #type: ignore
            if self.request.user.groups.filter(name='Manager').exists() == False: #type: ignore
                return Response({"message":"forbidden"}, 403)
        
        user = get_object_or_404(User, username=request.data['username'])
        dc = Group.objects.get(name="Delivery Crew")
        dc.user_set.add(user) #type: ignore
        return Response({"message": "user added to the delivery crew group"}, 200)

    def destroy(self, request):
        #only for super admin and managers
        if self.request.user.is_superuser == False: #type: ignore
            if self.request.user.groups.filter(name='Manager').exists() == False: #type: ignore
                return Response({"message":"forbidden"}, 403)
        user = get_object_or_404(User, username=request.data['username'])
        dc = Group.objects.get(name="Delivery Crew")
        dc.user_set.remove(user) #type: ignore
        return Response({"message": "user removed from the delivery crew group"}, 200)