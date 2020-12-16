import random
import re
from datetime import datetime, timedelta

import coreapi
import coreschema
from django.http import QueryDict
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.schemas import ManualSchema
from rest_framework.views import APIView

from capp_api.models import User, Consultant, CreditInfo, CreditLogs, Price
from django.shortcuts import render

from capp_api import parameters
from capp_api.serializer import UserSerializer, ConsultantSerializer, CreditSerializer, PriceSerializer
from capp_api.tasks import check_user_otp


# Create your views here.


def random_otp():
    """ This generates a random and unique key """
    key = random.randint(100001, 999999)
    try:
        User.objects.get(password=key)
        random_otp()
    except User.DoesNotExist:
        return key


@api_view(['POST'])
def generate_otp(request):
    """
    This gets a phone number and generates an otp code for it.
    If it is successful it returns 201 status code
    otherwise it returns 400 or 406 status code and error message in 'error' field.
    Example of POST request: {phone_number:+989159999999}
    :parameter {phone_number: requierd}
    """
    phone_number = request.data.get('phone_number', None)
    if phone_number:
        if not re.match(r'^\+[1-9]{1}[0-9]{7,11}$', phone_number):
            return Response({'status': 'error', 'error': "phone_number isn't in correct."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            User.objects.get(phone_number=phone_number)
            return Response({'status': 'error', 'error': 'This phone number is registered before.'},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        except User.DoesNotExist:
            try:
                otp = random_otp()
                user = User.objects.create(phone_number=phone_number, password=otp)
                # send_date = datetime.now() + timedelta(seconds=10)
                # check_user_otp.apply_async((user.pk, ), countdown=10)
                return Response({'status': 'successful'}, status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_406_NOT_ACCEPTABLE)
    else:
        return Response({'status': 'error', 'error': "There is no 'phone_number' field in request"},
                        status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def verify_otp(request):
    """
    This gets a phone number and otp and verifies this number.
    If it is successful it returns 200 status code and toke in 'token' field
    otherwise it returns 400 or 404 status code and error message in 'error' field.
    Example of POST request: {phone_number:+989159999999, otp:123456}
    """
    phone_number = request.data.get('phone_number', None)
    otp = request.data.get('otp', None)
    if phone_number and otp:
        try:
            user = User.objects.get(phone_number=phone_number, password=otp)
        except User.DoesNotExist:
            return Response({'status': 'error', 'error': 'phone_number or otp is invalid.'},
                            status=status.HTTP_404_NOT_FOUND)

        user.phone_verified = True
        user.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({'status': 'successful', 'token': token.key}, status=status.HTTP_200_OK)
    else:
        return Response({'status': 'error', 'error': "There is no 'phone_number' or 'otp' field in request"},
                        status=status.HTTP_400_BAD_REQUEST)


class UserInfo(APIView):
    serializer_class = UserSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """
        This gets a request with token and after authentication returns user details
        If it is successful it returns 200 status code and user details: ('email', 'first_name', 'last_name', 'image',
        'is_active', 'is_super_user', 'phone_number', 'phone_verified', 'username')
        otherwise it returns 406 status code and error message in 'error' field.
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        serializer = self.serializer_class(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        """
        This gets a request with token and after authentication, updates user infos according to data in request.
        If it is successful it returns 200 status code and new user details: ('email', 'first_name', 'last_name', 'image',
        'is_active', 'is_super_user', 'phone_number', 'phone_verified', 'username')
        otherwise it returns 406 status code and error message in 'error' field.
        Example of PUT request: {first_name: Majid, username: MA}
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        serializer = self.serializer_class(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreditAPI(APIView):
    serializer_class = CreditSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        """
        This gets a post request with token and after authentication creates a credit for that user.
        If it is successful it returns 201 status code and credit infos: ('credit', 'currency')
        otherwise it returns 400 or 404 status code and error message in 'error' field.
        Example of POST request: {currency=IRR}
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            CreditInfo.objects.get(user=request.user)
            return Response({'status': 'error', 'error': "This user has a credit right now."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        except:
            pass
        try:
            currency = request.data.get('currency', None)
            if currency not in ['USD', 'IRR']:
                return Response({'status': 'error', 'error': "Currency must be USD or IRR."},
                                status=status.HTTP_406_NOT_ACCEPTABLE)
            credit = CreditInfo(currency=currency, user=request.user)
            credit.save()
            # serializer.is_valid(raise_exception=True)
            # serializer.save()
            data = {'status': 'successful', 'credit': credit.credit, 'currency': credit.currency}
            return Response(data, status=status.HTTP_201_CREATED)
        except:
            return Response({'status': 'error', 'error': "Request don't have required data"},
                            status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """
        This gets a request with token and after authentication returns credit details.
        If it is successful it returns 200 status code and credit infos: ('credit', 'currency')
        otherwise it returns 400 or 404 status code and error message in 'error' field.
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            credit = CreditInfo.objects.get(user=request.user)
        except:
            return Response({'status': 'error', 'error': "This user doesn't have a credit."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            serializer = self.serializer_class(credit)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """
        This gets a request with token and after authentication returns new credit info.
        If it is successful it returns 200 status code and credit infos: ('credit', 'currency')
        otherwise it returns 400 or 404 status code and error message in 'error' field.
        Example of PUT request: {credit=24}
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            credit = CreditInfo.objects.get(user=request.user)
        except:
            return Response({'status': 'error', 'error': "This user doesn't have a credit."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        if request.data.get('currency', None):
            return Response({'status': 'error', 'error': "Changing currency is not acceptable."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer = self.serializer_class(credit, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class ConsultantAPI(APIView):
    serializer_class = ConsultantSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        """
        This gets a post request with token and after authentication creates a consultant for that user.
        If it is successful it returns 201 status code and consultant infos: ('type', 'presentation')
        otherwise it returns 400 or 406 status code and error message in 'error' field.
        Example of POST request: {type=nutrition, presentation="best consultant"}
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            credit_info = CreditInfo.objects.get(user=request.user)
        except CreditInfo.DoesNotExist:
            return Response({'status': 'error', 'error': 'You must create a credit at first.'},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        consultant_type = request.data.get('type', None)
        if not consultant_type:
            return Response({'status': 'error', 'error': 'There is no type field.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            Consultant.objects.get(user=request.user, type=consultant_type)
            return Response({'status': 'error', 'error': 'Consultant with this type is already exist.'},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        except:
            pass

        is_more_consultant = False
        if Consultant.objects.filter(user=request.user).count() > 0:  # First creation consultant is free
            is_more_consultant = True
            low_money = False
            message = ''
            if credit_info.currency == 'IRR':
                if credit_info.credit < parameters.BEING_CONSULTANT_IRR:
                    low_money = True
                    message = 'Your credit is lower than {} IRR.'.format(parameters.BEING_CONSULTANT_IRR)
            else:
                if credit_info.credit < parameters.BEING_CONSULTANT_USD:
                    low_money = True
                    message = 'Your credit is lower than {} USD.'.format(parameters.BEING_CONSULTANT_USD)
            if low_money:
                return Response({'status': 'error', 'error': message}, status=status.HTTP_406_NOT_ACCEPTABLE)

        try:
            consultant_type = request.data.get('type')
            presentation = request.data.get('presentation')
            if consultant_type not in parameters.CONSULTANT_TYPE:
                return Response({'status': 'error', 'error': 'Consultant type is not valid'},
                                status=status.HTTP_400_BAD_REQUEST)

            consultant = Consultant.objects.create(user=request.user, type=consultant_type, presentation=presentation)
            if is_more_consultant:
                text = 'title: being consultant\n'
                text += 'before: ' + str(credit_info.credit) + ' ' + credit_info.currency + '\n'
                if credit_info.currency == 'IRR':
                    credit_info.credit = credit_info.credit - parameters.BEING_CONSULTANT_IRR
                    credit_info.save()
                else:
                    credit_info.credit = credit_info.credit - parameters.BEING_CONSULTANT_USD
                    credit_info.save()
                text += 'after: ' + str(credit_info.credit) + ' ' + credit_info.currency + '\n'
            else:
                text = 'title: Creating free consultant for user\n'
                text += 'before: ' + str(credit_info.credit) + ' ' + credit_info.currency + '\n'
                text += 'after: ' + str(credit_info.credit) + ' ' + credit_info.currency + '\n'

            credit_log = CreditLogs.objects.create(credit=credit_info, text=text)
            consultant.credit_log = credit_log
            consultant.save()
            return Response(
                {'status': 'successful', 'consultant_type': consultant.type, 'presentation': consultant.presentation},
                status=status.HTTP_201_CREATED)
        except:
            return Response({'status': 'error', 'error': "Request doesn't have required infos"},
                            status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """
        This gets a request with token and after authentication returns all consultants details that user.
        If it is successful it returns 200 status code and consultant infos: list of ('type', 'presentation')
        otherwise it returns 400 or 406 status code and error message in 'error' field.
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            consultants = Consultant.objects.filter(user=request.user)
        except:
            return Response({'status': 'error'}, status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            serializer = self.serializer_class(consultants, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response({'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """
        This gets a request with token and after authentication returns new consultant info.
        If it is successful it returns 200 status code and consultant infos: ('type', 'presentation')
        otherwise it returns 400 or 406 status code and error message in 'error' field.
        Example of PUT request: {'old_type':'nutrition', 'type':'sports', 'presentation': "new presentation"}
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        if request.data.get('score', None):
            return Response({'status': 'error', 'error': "Changing score is not acceptable."},
                            status=status.HTTP_400_BAD_REQUEST)
        old_type = request.data.get('old_type', None)
        if not old_type:
            return Response({'status': 'error', 'error': "There isn't old type field."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            consultant = Consultant.objects.get(user=request.user, type=old_type)
        except:
            return Response({'status': 'error', 'error': "There isn't any consultant with these infos."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            serializer = self.serializer_class(consultant, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        """
        This gets a request with token and after authentication delete that consultant.
        If it is successful it returns 200 status code
        otherwise it returns 400 or 406 status code and error message in 'error' field.
        Example of DELETE request: {type=sports}
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        type = kwargs.get('type', None)
        if not type:
            return Response({'status': 'error', 'error': "There isn't type in url."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            consultant = Consultant.objects.get(user=request.user, type=type)
        except:
            return Response({'status': 'error', 'error': "There isn't any consultant with these infos."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            consultant.delete()
            return Response({'status': 'successful'}, status=status.HTTP_200_OK)
        except:
            return Response({'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)


class PriceAPI(APIView):
    serializer_class = PriceSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        """
        This gets a post request with token and after authentication creates prices for that consultant.
        If it is successful it returns 201 status code
        otherwise it returns 400 or 406 status code and error message in 'error' field.
            Example of POST request: {'type': 'sports', 'items': [{'times': "1,2,3", 'cost': 10}, {'times': "4,5.6", 'cost': 20}]}
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        consultant_type = request.data.get('type', None)
        items = request.data.get('items', None)
        if not consultant_type or not items:
            return Response({'status': 'error', 'error': "There isn't type field or items field."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            consultant = Consultant.objects.get(user=request.user, type=consultant_type)
        except Consultant.DoesNotExist:
            return Response({'status': 'error', 'error': 'You must create a consultant at first.'},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            for price in consultant.prices.all():
                price.delete()
        except:
            return Response({'status': 'error', 'error': "Saving new prices can't be completed."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            items_list = []
            time_numbers = set()
            for item in items:
                """ Checking time numbers """
                new_times = set(item['times'].split(','))
                if len(time_numbers.intersection(new_times)) > 0 and time_numbers:
                    return Response({'status': 'error', 'error': 'Some of time numbers are common.'},
                                    status=status.HTTP_400_BAD_REQUEST)
                time_numbers.update(new_times)

                data = {'consultation': consultant.pk}
                data.update(item)
                items_list.append(data)
            serializer = self.serializer_class(data=items_list, many=True)

            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({'status': 'successful', 'data': serializer.data},
                            status=status.HTTP_201_CREATED)
        except:
            return Response({'status': 'error'},
                            status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """
        This gets a PUT request with token and after authentication removes old infos and creates prices for that consultant.
        If it is successful it returns 201 status code
        otherwise it returns 400 or 406 status code and error message in 'error' field.
        Example of PUT request: {'type': 'sports', 'items': [{'times': "1,2,3", 'cost': 10}, {'times': "4,5.6", 'cost': 20}]}
        """
        # if not request.user.phone_verified:
        #     return Response({'status': 'error', 'error': "Phone of this user is not verified."},
        #                     status=status.HTTP_406_NOT_ACCEPTABLE)
        # consultant_type = request.data.get('type', None)
        # items = request.data.get('items', None)
        # if not consultant_type or not items:
        #     return Response({'status': 'error', 'error': "There isn't type field or items field."},
        #                     status=status.HTTP_400_BAD_REQUEST)
        # try:
        #     consultant = Consultant.objects.get(user=request.user, type=consultant_type)
        # except Consultant.DoesNotExist:
        #     return Response({'status': 'error', 'error': 'You must create a consultant at first.'},
        #                     status=status.HTTP_406_NOT_ACCEPTABLE)
        # try:
        #     for price in consultant.prices.all():
        #         price.delete()
        # except:
        #     return Response({'status': 'error', 'error': "changing prices can't become complete."},
        #                     status=status.HTTP_406_NOT_ACCEPTABLE)
        return self.post(request)

    def get(self, request, *args, **kwargs):
        """
        This gets a post request with token and after authentication returns all prices of that consultant.
        If it is successful it returns 200 status code
        otherwise it returns 400 or 406 status code and error message in 'error' field.
        Example of GET request url: http://127.0.0.1:8000/price/sports/
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        consultant_type = kwargs.get('type', None)
        if not consultant_type:
            return Response({'status': 'error', 'error': "There isn't type field."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            consultant = Consultant.objects.get(user=request.user, type=consultant_type)
        except Consultant.DoesNotExist:
            return Response({'status': 'error', 'error': 'You must create a consultant at first.'},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            serializer = self.serializer_class(consultant.prices, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response({'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        """
        This gets a post request with token and after authentication delete one or all prices of that consultant
        If it is successful it returns 200 status code
        otherwise it returns 400 or 406 status code and error message in 'error' field.
        Example of DELETE request url: DELETE http://127.0.0.1:8000/price/sports/all/
        Example of DELETE request url: DELETE http://127.0.0.1:8000/price/sports/300/
        """
        if not request.user.phone_verified:
            return Response({'status': 'error', 'error': "Phone of this user is not verified."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)

        consultant_type = kwargs.get('type', None)
        cost = kwargs.get('cost', None)
        if not consultant_type or not cost:
            return Response({'status': 'error', 'error': "There isn't type field or cost field."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            consultant = Consultant.objects.get(user=request.user, type=consultant_type)
        except Consultant.DoesNotExist:
            return Response({'status': 'error', 'error': "You don't have consultant with this type."},
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            if cost == 'all':
                for prise in consultant.prices.all():
                    prise.delete()
                return Response({'status': 'successful'}, status=status.HTTP_200_OK)
            else:
                try:
                    price = Price.objects.get(consultation=consultant, cost=cost)
                    price.delete()
                    return Response({'status': 'successful'}, status=status.HTTP_200_OK)
                except:
                    return Response({'status': "There isn't price with this infos"}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

