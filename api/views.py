from rest_framework.permissions import IsAuthenticated, IsAdminUser, SAFE_METHODS
from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from .models import Category, MenuItem, Cart, Order, OrderItem
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
from . import serializers
from .permissions import IsManager
from rest_framework.decorators import api_view
from .utils import calc_pages

def check_given_permissions(self):
    permission_classes = []
    if self.request.method not in SAFE_METHODS:
        permission_classes.append(IsManager)
    return [permission() for permission in permission_classes] 
    
class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer
    ordering_fields = ['title']
    def get_permissions(self):
        return check_given_permissions(self)

class SingleCategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer
    def get_permissions(self):
        return check_given_permissions(self)

class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = serializers.MenuItemSerializer
    search_fields = ['category__title']
    ordering_fields = ['price']

    def get_permissions(self):
        return check_given_permissions(self)
    
class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = serializers.MenuItemSerializer

    def get_permissions(self):
        return check_given_permissions(self)
    
class CartView(generics.ListCreateAPIView):
    queryset = Cart.objects.all()
    serializer_class = serializers.CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user = self.request.user)

    def delete(self, request, *args, **kwargs):
        Cart.objects.filter(user = request.user).delete()
        return Response({"message": "deleted cart"}, status=status.HTTP_204_NO_CONTENT)

class SingleCartItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Cart.objects.all()
    serializer_class = serializers.CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user = self.request.user)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        quantity = request.data.get('quantity')
        instance.quantity = quantity
        instance.price = instance.unit_price * int(quantity)
        instance.save()
        return Response({"message": "Order updated"}, status=status.HTTP_200_OK)
                                                                                                                                                                            
class OrderView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = serializers.OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.groups.count() == 0:
            return Order.objects.filter(user = self.request.user)
        elif self.request.user.groups.filter(name = 'delivery_crew').exists():
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
            return Response(order_serializer.data, status=status.HTTP_201_CREATED)
        
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
            return Response({"message": "Not Authorized"}, status=status.HTTP_403_FORBIDDEN)
        
        instance = self.get_object()
        if request.user.groups.filter(name="delivery_crew").exists():
            state = request.data.get("status")
            if state is not None:
                instance.status = state
                instance.save()
                return Response({"message": "Order status updated"}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Status not provided"}, status=status.HTTP_400_BAD_REQUEST)
        elif request.user.groups.filter(name="manager").exists():
            delivery_crew_id = request.data.get('delivery_crew')
            state = request.data.get("status")
            if delivery_crew_id is not None:
                delivery_crew = get_object_or_404(User, id=delivery_crew_id)
                instance.delivery_crew = delivery_crew
            if state is not None:
                instance.status = state

            instance.save()
            return Response({"message": "Order updated"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Not Authorized"}, status=status.HTTP_403_FORBIDDEN)
            
class ManagerViewSet(viewsets.ViewSet): 
    permission_classes = [IsAdminUser]
    def list(self, request):
        user = User.objects.all().filter(groups__name='manager')
        items = serializers.UserSerializer(user, many=True)
        return Response(items.data, status=status.HTTP_200_OK)
    
    def create(self, request):
        user = get_object_or_404(User, username=request.data['username'])
        managers = Group.objects.get(name="Manager")
        managers.user_set.add(user)
        return Response({"message": "user added to the manager group"}, status=status.HTTP_200_OK)
    
    def destroy(self, request):
        user = get_object_or_404(User, username=request.data['username'])
        managers = Group.objects.get(name="Manager")
        managers.user_set.remove(user) 
        return Response({"message": "user removed from the manager group"}, status=status.HTTP_200_OK)
    
class DeliveryCrewViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    def list(self, request):
        users = User.objects.all().filter(groups__name='delivery_crew')
        items = serializers.UserSerializer(users, many=True)
        return Response(items.data, status=status.HTTP_200_OK)

    def create(self, request):
        if self.request.user.is_superuser == False:
            if self.request.user.groups.filter(name='Manager').exists() == False:
                return Response({"message":"forbidden"}, status=status.HTTP_403_FORBIDDEN)
        
        user = get_object_or_404(User, username=request.data['username'])
        dc = Group.objects.get(name="delivery_crew")
        dc.user_set.add(user)
        return Response({"message": "user added to the delivery crew group"}, status=status.HTTP_200_OK)

    def destroy(self, request):
        if self.request.user.is_superuser == False:
            if self.request.user.groups.filter(name='Manager').exists() == False:
                return Response({"message":"forbidden"}, status.HTTP_403_FORBIDDEN)

        user = get_object_or_404(User, username=request.data['username'])
        dc = Group.objects.get(name="delivery_crew")
        dc.user_set.remove(user)
        return Response({"message": "user removed from the delivery crew group"}, status=status.HTTP_200_OK)


@api_view(['GET'])
def total_menu_items(request):
    if request.method == 'GET':
        search_slug = request.query_params.get('category')
        if search_slug is not None:
            menuitem_count = MenuItem.objects.filter(category__slug=search_slug).count()
            total_pages = calc_pages(menuitem_count, 12)
            return Response({"counts": menuitem_count, "total_pages": total_pages}, status=status.HTTP_200_OK)
        else:
            menuitem_count = MenuItem.objects.all().count()
            total_pages = calc_pages(menuitem_count, 12)
            return Response({"counts": menuitem_count, "total_pages": total_pages}, status=status.HTTP_200_OK)