from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, force_authenticate, APIRequestFactory
from django.contrib.auth.models import User
from .models import Cart, MenuItem, Category, Order
from .views import CategoriesView 
from . import serializers
import json
# Create your tests here.
    
class SerializerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='Test_user')
        self.category = Category.objects.create(title="Test_category")
        self.menu_item = MenuItem.objects.create(title="Test_menu_item", price = 10, category = self.category)
        cart_serializer = serializers.CartSerializer(data = {'user': self.user.id, 'menuitem': self.menu_item.id, 'quantity': 2})
        if cart_serializer.is_valid(raise_exception=True):
            self.cart = cart_serializer.save()
    
    def test_category_serializer(self):
        serializer = serializers.CategorySerializer(instance=self.category)
        self.assertEqual(serializer.data['title'], 'Test_category')

    def test_menu_item_serializer(self):
        serializer = serializers.MenuItemSerializer(instance=self.menu_item)
        self.assertEqual(serializer.data['title'], 'Test_menu_item')
        self.assertEqual(float(serializer.data['price']), 10)
        self.assertEqual(serializer.data['category_name'], 'Test_category')

    def test_cart_serializer(self):
        serializer = serializers.CartSerializer(instance=self.cart)
        self.assertEqual(serializer.data['user'], self.user.id)

        total_price = self.menu_item.price * self.cart.quantity
        self.assertEqual(float(serializer.data['unit_price']), self.menu_item.price)
        self.assertEqual(float(serializer.data['price']), total_price)

class CategoriesViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='Test_user', password="Test_user")
        Category.objects.create(title="Test_category")
        self.client = APIClient()
        self.urls = reverse('categories')
    
    def test_get_categories(self):
        response = self.client.get(self.urls)
        self.assertJSONEqual(json.dumps(response.data["results"]), [{"id": 1, "title": "Test_category"}])
    
    def test_post_categories(self):
        response = self.client.post(self.urls, {'title': 'Test_category2'})
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.urls, {'title': 'Test_category2'})
        self.assertEqual(response.status_code, 403)

        self.user.groups.create(name='manager')
        response = self.client.post(self.urls, {'title': 'Test_category2'})
        self.assertEqual(response.status_code, 201)

class MenuItemViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='Test_user', password="Test_user")
        self.category = Category.objects.create(title="Test_category")
        MenuItem.objects.create(title="Test_menu_item", price = 10, category = Category.objects.get(title="Test_category"))
        self.client = APIClient()
        self.urls = reverse('menu_items')
    
    def test_get_menu_items(self):
        res = self.client.get(self.urls)
        self.assertEqual(res.status_code, 200)

    def test_post_menu_items(self):
        res = self.client.post(self.urls, {'title': 'Test_menu_item2', 'price': 20, 'category': self.category})
        self.assertEqual(res.status_code, 403)

        self.client.force_authenticate(user=self.user)
        res = self.client.post(self.urls, {'title': 'Test_menu_item2', 'price': 20, 'category': self.category})
        self.assertEqual(res.status_code, 403)

        self.user.groups.create(name='manager')
        res = self.client.post(self.urls, {'title': 'Test_menu_item2', 'price': 20, 'category': self.category.id})
        self.assertEqual(res.status_code, 201)

