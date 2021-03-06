from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Tag, Recipe
from recipe.serializers import TagSerializer


TAG_URL = reverse('recipe:tag-list')


class PublicTagAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        res = self.client.get(TAG_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagAPITests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create(
            email='test@mail.com',
            password='pass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        Tag.objects.create(user=self.user, name='test 1')
        Tag.objects.create(user=self.user, name='test 2')
        res = self.client.get(TAG_URL)
        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        user2 = get_user_model().objects.create(
            email='test2@mail.com',
            password='pass123'
        )
        Tag.objects.create(user=user2, name='test 1')
        tag = Tag.objects.create(user=self.user, name='test 2')
        res = self.client.get(TAG_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)

    def test_create_tag_successfull(self):
        payload = {'name': 'test'}
        self.client.post(TAG_URL, payload)
        exists = Tag.objects.filter(
            name=payload['name'],
            user=self.user
        ).exists()
        self.assertTrue(exists)

    def test_create_tag_invalid(self):
        payload = {'name': ''}
        res = self.client.post(TAG_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_tags_assigned_to_recipe(self):
        tag1 = Tag.objects.create(user=self.user, name='tag 1')
        tag2 = Tag.objects.create(user=self.user, name='tag 2')
        recipe = Recipe.objects.create(
            title='test title',
            time_minutes=10,
            price=5.00,
            user=self.user
        )
        recipe.tags.add(tag1)
        res = self.client.get(TAG_URL, {'assigned_only': 1})
        serializer1 = TagSerializer(tag1)
        serializer2 = TagSerializer(tag2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_tags_assigned_unique(self):
        """Test filtering tags by assigning returns unique items"""
        tag1 = Tag.objects.create(user=self.user, name='tag 1')
        Tag.objects.create(user=self.user, name='tag 2')
        recipe1 = Recipe.objects.create(
            title='recipe 1',
            time_minutes=10,
            price=5.00,
            user=self.user
        )
        recipe1.tags.add(tag1)
        recipe2 = Recipe.objects.create(
            title='recipe 2',
            time_minutes=10,
            price=5.00,
            user=self.user
        )
        recipe2.tags.add(tag1)
        res = self.client.get(TAG_URL, {'assigned_only': 1})
        self.assertEqual(len(res.data), 1)
