from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

UserModel = get_user_model()


class AccountsAuthTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.change_email_url = reverse('change-email')
        self.change_password_url = reverse('change-password')
        self.token_refresh_url = reverse('token-refresh')

        self.user_password = 'StrongPass123!'
        self.user = UserModel.objects.create_user(
            email='testuser@example.com',
            password=self.user_password
        )

    def authenticate_client(self, user=None):
        """
        Adds a valid JWT access token to the test client.
        """
        user = user or self.user
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        return refresh

    def test_register_user_success(self):
        payload = {
            'email': 'newuser@example.com',
            'password': 'NewStrongPass123!'
        }

        response = self.client.post(self.register_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UserModel.objects.filter(email='newuser@example.com').exists())

        user = UserModel.objects.get(email='newuser@example.com')
        self.assertNotEqual(user.password, payload['password'])
        self.assertTrue(user.check_password(payload['password']))

    def test_register_user_with_existing_email_fails(self):
        payload = {
            'email': 'testuser@example.com',
            'password': 'AnotherStrongPass123!'
        }

        response = self.client.post(self.register_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(UserModel.objects.filter(email='testuser@example.com').count(), 1)

    def test_login_success(self):
        payload = {
            'email': 'testuser@example.com',
            'password': self.user_password
        }

        response = self.client.post(self.login_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('refresh', response.data)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['message'], 'Login successful')

    def test_login_with_wrong_password_fails(self):
        payload = {
            'email': 'testuser@example.com',
            'password': 'WrongPassword123!'
        }

        response = self.client.post(self.login_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_login_with_nonexistent_email_fails(self):
        payload = {
            'email': 'missing@example.com',
            'password': 'SomePassword123!'
        }

        response = self.client.post(self.login_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_token_refresh_success(self):
        refresh = RefreshToken.for_user(self.user)

        payload = {
            'refresh': str(refresh)
        }

        response = self.client.post(self.token_refresh_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_logout_success(self):
        refresh = RefreshToken.for_user(self.user)

        payload = {
            'refresh': str(refresh)
        }

        response = self.client.post(self.logout_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Logout successful')

    def test_logout_with_invalid_token_fails(self):
        payload = {
            'refresh': 'invalid.token.value'
        }

        response = self.client.post(self.logout_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Invalid or expired token')

    def test_change_email_success(self):
        self.authenticate_client()

        payload = {
            'new_email': 'updated@example.com',
            'current_password': self.user_password
        }

        response = self.client.patch(self.change_email_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Email changed successfully.')
        self.assertEqual(response.data['email'], 'updated@example.com')

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated@example.com')

    def test_change_email_requires_authentication(self):
        payload = {
            'new_email': 'updated@example.com',
            'current_password': self.user_password
        }

        response = self.client.patch(self.change_email_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_email_with_wrong_current_password_fails(self):
        self.authenticate_client()

        payload = {
            'new_email': 'updated@example.com',
            'current_password': 'WrongPassword123!'
        }

        response = self.client.patch(self.change_email_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'testuser@example.com')

    def test_change_email_to_existing_email_fails(self):
        other_user = UserModel.objects.create_user(
            email='existing@example.com',
            password='OtherStrongPass123!'
        )
        self.assertIsNotNone(other_user)

        self.authenticate_client()

        payload = {
            'new_email': 'existing@example.com',
            'current_password': self.user_password
        }

        response = self.client.patch(self.change_email_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'testuser@example.com')


    def test_change_password_success(self):
        self.authenticate_client()

        payload = {
            'current_password': self.user_password,
            'new_password': 'MyBrandNewPass123!',
            'confirm_new_password': 'MyBrandNewPass123!'
        }

        response = self.client.post(self.change_password_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password changed successfully.')

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('MyBrandNewPass123!'))
        self.assertFalse(self.user.check_password(self.user_password))

    def test_change_password_requires_authentication(self):
        payload = {
            'current_password': self.user_password,
            'new_password': 'MyBrandNewPass123!',
            'confirm_new_password': 'MyBrandNewPass123!'
        }

        response = self.client.post(self.change_password_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_with_wrong_current_password_fails(self):
        self.authenticate_client()

        payload = {
            'current_password': 'WrongPassword123!',
            'new_password': 'MyBrandNewPass123!',
            'confirm_new_password': 'MyBrandNewPass123!'
        }

        response = self.client.post(self.change_password_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.user_password))

    def test_change_password_with_non_matching_confirmation_fails(self):
        self.authenticate_client()

        payload = {
            'current_password': self.user_password,
            'new_password': 'MyBrandNewPass123!',
            'confirm_new_password': 'DifferentPass123!'
        }

        response = self.client.post(self.change_password_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.user_password))

    def test_change_password_with_same_password_succeeds(self):
        self.authenticate_client()

        payload = {
            'current_password': self.user_password,
            'new_password': self.user_password,
            'confirm_new_password': self.user_password
        }

        response = self.client.post(self.change_password_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password changed successfully.')

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.user_password))

    def test_change_password_allows_weak_or_short_password(self):
        self.authenticate_client()

        payload = {
            'current_password': self.user_password,
            'new_password': '123',
            'confirm_new_password': '123'
        }

        response = self.client.post(self.change_password_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password changed successfully.')

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('123'))
        self.assertFalse(self.user.check_password(self.user_password))

    def test_user_can_login_with_new_password_after_password_change(self):
        self.authenticate_client()

        change_payload = {
            'current_password': self.user_password,
            'new_password': 'NewestPassword123!',
            'confirm_new_password': 'NewestPassword123!'
        }

        change_response = self.client.post(self.change_password_url, change_payload, format='json')
        self.assertEqual(change_response.status_code, status.HTTP_200_OK)

        self.client.credentials()

        old_login_response = self.client.post(
            self.login_url,
            {
                'email': 'testuser@example.com',
                'password': self.user_password
            },
            format='json'
        )
        self.assertEqual(old_login_response.status_code, status.HTTP_401_UNAUTHORIZED)

        new_login_response = self.client.post(
            self.login_url,
            {
                'email': 'testuser@example.com',
                'password': 'NewestPassword123!'
            },
            format='json'
        )
        self.assertEqual(new_login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', new_login_response.data)
        self.assertIn('refresh', new_login_response.data)
