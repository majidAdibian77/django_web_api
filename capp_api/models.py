from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from capp_api import parameters

# Create your models here.


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""
    use_in_migrations = True

    def _create_user(self, phone_number, password, **extra_fields):
        """Create and save a User with the given phone_number and password."""
        if not phone_number:
            raise ValueError('The given phone_number must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone_number, password=None, **extra_fields):
        """Create and save a regular User with the given phone_number and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number, password, **extra_fields):
        """Create and save a SuperUser with the given phone_number and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(phone_number, password, **extra_fields)


class User(AbstractUser):
    username = models.CharField(max_length=20, default=None, null=True, blank=True)
    # password = models.CharField(max_length=6, validators=[MinLengthValidator(6)], unique=True)
    phone_regex = RegexValidator(regex=r'^\+[1-9]{1}[0-9]{7,11}$', message="Phone number must be entered in the"
                                                                           " format: '+99999999'. Up to 15 digits allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, primary_key=True, null=False,
                                    blank=False, unique=True)  # validators should be a list
    # phone_number = models.CharField(max_length=13, validators=[MinLengthValidator(13)], primary_key=True, null=False,
    #                                 blank=False, unique=True)
    first_name = models.CharField(max_length=20, null=True, blank=True)
    last_name = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    is_super_user = models.BooleanField(default=False)
    image = models.ImageField(upload_to='profile_users', default="images/profile_image.png", null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    USERNAME_FIELD = 'phone_number'
    objects = UserManager()

    def __str__(self):
        return self.phone_number


class Consultant(models.Model):
    all_consultant_types = ((item, item) for item in parameters.CONSULTANT_TYPE)
    user = models.ForeignKey(User, related_name='consultant', null=False, on_delete=models.CASCADE)
    score = models.IntegerField(null=False, blank=False, default=0,
                                validators=[MinValueValidator(0), MaxValueValidator(1000)])
    type = models.CharField(max_length=20, default='educational', choices=all_consultant_types, null=False, blank=False)
    presentation = models.TextField(null=False, blank=False)
    credit_log = models.OneToOneField(CreditLogs, on_delete=models.SET_NULL, related_name='being_consultant',
                                      null=True)  # Because of creating credit log after creating consultant

    class Meta:
        unique_together = ('user', 'type',)

    def __str__(self):
        return self.type


class Price(models.Model):
    time_number_regix = RegexValidator(regex=r"^[1-9]{1}[0-9]{0,2}(,[1-9]{1}[0-9]{0,2})*$",
                                       message="times must be in this format: 2,34,56,...")
    times = models.TextField(validators=[time_number_regix], max_length=500, null=False, blank=False)
    cost = models.IntegerField(validators=[MinValueValidator(0)], null=False)
    consultation = models.ForeignKey(Consultant, related_name='prices', null=False, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('cost', 'consultation'),)

    def __str__(self):
        return str(self.consultation) + ': ' + str(self.cost)


class BuyingConsultant(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET(0), related_name='buying_consultant', null=False)
    consultant = models.ForeignKey(Consultant, on_delete=models.SET(0), related_name='buying_consultant', null=False)
    credit_log = models.OneToOneField(CreditLogs, on_delete=models.SET(0), related_name='buying_consultant',
                                      null=False)
    consulting_time = models.TextField(max_length=500, null=False, blank=False)

    def __str__(self):
        return str(self.user) + ' buy ' + str(self.consultant)


class Plan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plans', null=False)
    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE, related_name='plans', null=True, default=None)
    title = models.CharField(max_length=50, null=False, blank=False)
    priority = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)], null=False, default=5)
    is_consulting = models.BooleanField(null=False, default=False)
    user_extra_info = models.TextField(max_length=500, null=True, blank=True)

    def __str__(self):
        return str(self.user) + ': ' + str(self.title)


class Items(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='items', null=False)
    item_name = models.CharField(max_length=50, null=False, blank=False)
    start_time = models.DateTimeField(null=False)
    end_time = models.DateTimeField(null=False)
    alarm_is_active = models.BooleanField(null=False, default=False)
    importance = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], default=50, null=False)
    progress = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], default=0, null=False)

    def __str__(self):
        return str(self.plan) + ': ' + str(self.item_name)
