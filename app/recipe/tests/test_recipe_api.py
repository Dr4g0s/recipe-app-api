from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer
import tempfile
import os
from PIL import Image


RECIPE_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def sample_tag(user, name='test tag'):
    return Tag.objects.create(name=name, user=user)


def sample_ingredient(user, name='test ingredient'):
    return Ingredient.objects.create(name=name, user=user)


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_recipe(user, **params):
    default = {
        'title': 'test title',
        'time_minutes': 10,
        'price': 5.00
    }
    default.update(params)
    return Recipe.objects.create(user=user, **default)


class PublicRecipeAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        res = self.client.get(RECIPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@mail.com',
            password='pass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        sample_recipe(self.user)
        sample_recipe(self.user)
        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_detail_view(self):
        recipe = sample_recipe(self.user)
        recipe.tags.add(sample_tag(self.user))
        recipe.ingredients.add(sample_ingredient(self.user))
        url = detail_url(recipe.id)
        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_basic_recipe(self):
        payload = {
            'title': 'test title',
            'time_minutes': 10,
            'price': 5.00,
        }
        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        tag1 = sample_tag(self.user, 'tag 1')
        tag2 = sample_tag(self.user, 'tag 2')
        payload = {
            'title': 'test title',
            'time_minutes': 10,
            'price': 5.00,
            'tags': [tag1.id, tag2.id]
        }
        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        ingredient1 = sample_ingredient(self.user, 'ingredient1')
        ingredient2 = sample_ingredient(self.user, 'ingredient2')
        payload = {
            'title': 'test title',
            'time_minutes': 10,
            'price': 5.00,
            'ingredients': [ingredient1.id, ingredient2.id]
        }
        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_recipe_partial_update(self):
        recipe = sample_recipe(self.user)
        recipe.tags.add(sample_tag(self.user))
        new_tag = sample_tag(self.user, 'new tag')
        url = detail_url(recipe.id)
        payload = {'title': 'new title', 'tags': [new_tag.id]}
        res = self.client.patch(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 1)
        self.assertIn(new_tag, tags)

    def test_recipe_full_update(self):
        recipe = sample_recipe(self.user)
        recipe.tags.add(sample_tag(self.user))
        new_tag = sample_tag(self.user, 'new tag')
        payload = {
            'title': 'new title',
            'time_minutes': 1111,
            'price': 55.00,
            'tags': [new_tag.id]
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(recipe.price, payload['price'])
        self.assertEqual(
            list(recipe.tags.values_list('id', flat=True)),
            payload['tags']
        )


class RecipeUploadImageTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create(
            email='test@mail.com',
            password='pass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image_to_recipe(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            img = Image.new('RGB', (10, 10))
            img.save(ntf, format='JPEG')
            ntf.seek(0)
            res = self.client.post(url, {'image': ntf}, format='multipart')
        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_invalid(self):
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url, {'image': 'ivalid'}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_recipes_by_tags(self):
        recipe1 = sample_recipe(user=self.user, title='recipe 1')
        recipe2 = sample_recipe(user=self.user, title='recipe 2')
        recipe3 = sample_recipe(user=self.user, title='recipe 3')
        tag1 = sample_tag(self.user, 'tag 1')
        tag2 = sample_tag(self.user, 'tag 2')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        res = self.client.get(RECIPE_URL, {'tags': f'{tag1.id},{tag2.id}'})
        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_recipes_by_ingredients(self):
        recipe1 = sample_recipe(user=self.user, title='recipe 1')
        recipe2 = sample_recipe(user=self.user, title='recipe 2')
        recipe3 = sample_recipe(user=self.user, title='recipe 3')
        ingredient1 = sample_ingredient(self.user, 'ingredient 1')
        ingredient2 = sample_ingredient(self.user, 'ingredient 2')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)
        res = self.client.get(
            RECIPE_URL,
            {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        )
        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)
