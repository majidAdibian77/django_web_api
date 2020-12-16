from rest_framework import serializers
from capp_api.models import User, Consultant, CreditInfo, Price


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'image', 'is_super_user', 'phone_number', 'phone_verified', 'username')
        extra_kwargs = {'phone_verified': {'read_only': True},
                        'is_super_user': {'read_only': True},
                        'phone_number': {'read_only': True}}


class PriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = ('times', 'cost', 'consultation')
        extra_kwargs = {'consultation': {'write_only': True}}


class ConsultantSerializer(serializers.ModelSerializer):
    prices = PriceSerializer(many=True, read_only=True)

    class Meta:
        model = Consultant
        fields = ('score', 'type', 'presentation', 'prices')
        extra_kwargs = {'score': {'read_only': True}}


class CreditSerializer(serializers.ModelSerializer):
    # user = serializers.RelatedField(read_only=True)

    class Meta:
        model = CreditInfo
        fields = ('credit', 'currency')

    def update(self, instance, validated_data):
        validated_data['currency'] = instance.currency
        validated_data['user'] = instance.user
        instance = super().update(instance, validated_data)
        return instance
