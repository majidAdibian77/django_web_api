import json

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.reverse import reverse
from rest_framework.test import APIClient, APITestCase

from capp_api.models import User, CreditLogs, Consultant, Price


class UserTest(APITestCase):
    """ Test module for testing all function for user """

    def setUp(self):
        # self.client = APIClient()

        self.otp = 123456
        self.user = User.objects.create(phone_number='+989157408277', password=self.otp)

        self.valid_phone_number = {'phone_number': '+989157408270', }
        self.repetitive_phone_number = {'phone_number': '+989157408277', }
        self.invalid_phone_number = {'phone_number': '989157408277', }

        self.valid_otp = {"phone_number": "+989157408277", "otp": 123456}
        self.invalid_otp = {"phone_number": "+989157408277", "otp": 123455}
        self.valid_update_user = {'first_name': 'Majid', 'email': 'majid@gmail.com', 'password': '999999',
                                  'image': open('capp_api/test/profile.jpg', 'rb')}
        self.invalid_update_user = {'email': 'majid@gmail.com'}

    def test_create_valid_user(self):
        response = self.client.post(
            reverse('generate_otp'),
            data=json.dumps(self.valid_phone_number),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_repetitive_user(self):
        response = self.client.post(
            reverse('generate_otp'),
            data=json.dumps(self.repetitive_phone_number),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)

    def test_create_invalid_user(self):
        response = self.client.post(
            reverse('generate_otp'),
            data=json.dumps(self.invalid_phone_number),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)

    def test_verify_wrong_otp(self):
        response = self.client.post(
            reverse('verify_otp'),
            data=json.dumps(self.invalid_otp),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_correct_otp(self):
        verified_phone_number = self.user.phone_verified
        self.assertEqual(verified_phone_number, False)
        response = self.client.post(
            reverse('verify_otp'),
            data=json.dumps(self.valid_otp),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(phone_number='+989157408277')
        self.assertEqual(user.phone_verified, True)

    def test_get_and_update_user(self):
        self.client.post(
            reverse('verify_otp'),
            data=json.dumps(self.valid_otp),
            content_type='application/json'
        )
        token = Token.objects.get(user=self.user).key
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        response = self.client.get(
            reverse('user_info'),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.put(
            reverse('user_info'),
            data=self.valid_update_user,
            format='multipart'
        )
        # image = open('capp_api/test/profile.jpg', 'rb')
        print(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEquals([response.data['first_name'], response.data['last_name'], 'password' in response.data.keys(),
                           response.data['image'] is not None],
                          ['Majid', None, False, True])

        self.user.email = None
        self.user.save()
        self.test_verify_correct_otp()
        User.objects.create(phone_number='+989157408270', password='444444', email='majid@gmail.com')
        response = self.client.put(
            reverse('user_info'),
            data=json.dumps(self.invalid_update_user),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


def verify():
    client = APIClient()
    user = User.objects.create(phone_number='+989157408277', password=123456)
    valid_otp = {"phone_number": "+989157408277", "otp": 123456}
    client.post(
        reverse('verify_otp'),
        data=json.dumps(valid_otp),
        content_type='application/json'
    )
    token = Token.objects.get(user=user).key
    # self.client.force_authenticate(self.user, token='zdswrg2rfuhuidflvakbv')
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)
    return client, user


class ConsultantTest(APITestCase):
    """ Test module is for testing functions for consultant """

    def setUp(self):
        self.client, self.user = verify()
        response = self.client.post(
            reverse('credit'),
            data=json.dumps({'currency': 'IRR'}),
            content_type='application/json'
        )

    def test_create_consultant(self):
        """ request with invalid consultant type """
        response = self.client.post(
            reverse('consultant'),
            data=json.dumps({'type': 'spoots', 'presentation': 'I am testing'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        """ correct request """
        response = self.client.post(
            reverse('consultant'),
            data=json.dumps({'type': 'sports', 'presentation': 'I am testing'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        consultant = Consultant.objects.get(user=self.user)
        credit_log = consultant.credit_log
        self.assertEquals('title: Creating free consultant for user' in credit_log.text, True)

        """ Second request and getting error for low credit """
        response = self.client.post(
            reverse('consultant'),
            data=json.dumps({'type': 'sports', 'presentation': 'I am testing'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)

    def test_git_consultant(self):
        response = self.client.get(
            reverse('consultant'),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_put_consultant(self):
        self.test_create_consultant()
        response = self.client.put(
            reverse('consultant'),
            data=json.dumps({'old_type': 'sports', 'type': 'nutrition', 'presentation': "new presentation"}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([response.data.get('type'), response.data.get('presentation')],
                         ['nutrition', 'new presentation'])

        """ Request with wrong infos """
        response = self.client.put(
            reverse('consultant'),
            data=json.dumps({'old_type': 'sports', 'type': 'nutrition'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)

        """ Request with score field """
        response = self.client.put(
            reverse('consultant'),
            data=json.dumps({'old_type': 'nutrition', 'score': '20'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_consultant(self):
        self.test_create_consultant()
        response = self.client.delete(
            reverse('consultant'),
            data=json.dumps({'type': 'nutrition'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)

        response = self.client.delete(
            reverse('consultant'),
            data=json.dumps({'type': 'sports'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)