from django.urls import path, re_path
from capp_api import views

# Wire up our API using automatic URL routing.
urlpatterns = [
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('generate_otp/', views.generate_otp, name='generate_otp'),
    path('user_details/', views.UserInfo.as_view(), name='user_info'),
    path('consultant/', views.ConsultantAPI.as_view(), name='consultant'),
    re_path(r'^consultant/(?P<type>[\w]+)/$', views.ConsultantAPI.as_view(), name='delete_consultant'),

    path('price/', views.PriceAPI.as_view(), name='price'),
    re_path(r'^price/(?P<type>[\w]+)/$', views.PriceAPI.as_view(), name='get_price'),
    re_path(r'^price/(?P<type>[\w]+)/(?P<cost>[\w]+)/$', views.PriceAPI.as_view(), name='delete_price'),
]