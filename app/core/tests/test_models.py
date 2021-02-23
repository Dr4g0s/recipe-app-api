from django.test import TestCase
from django.contrib.auth import get_user_model
from core import models


def create_user(email='test@mail.com', password='pass123'):
    return get_user_model().objects.create_user(
        email=email,
        password=password
    )


class ModelTests(TestCase):

    def test_create_user_with_email(self):
        email = 'test@mail.com'
        password = 'pass123'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        email = "test@MAIL.COM"
        user = get_user_model().objects.create_user(
            email=email,
            password="pass123"
        )
        self.assertEqual(user.email, email.lower())

    def test_new_user_email_invalid(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(
                email=None,
                password="pass123"
            )

    def test_create_superuser(self):
        email = 'test@mail.com'
        user = get_user_model().objects.create_superuser(
            email=email,
            password="pass123"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_tag_str(self):
        tag = models.Tag.objects.create(
            user=create_user(),
            name='test'
        )
        self.assertEqual(str(tag), tag.name)
