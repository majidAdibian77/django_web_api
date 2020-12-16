from django.contrib import admin
from capp_api.models import User, PlanComments, BuyingConsultant, Responsible, Bill, Items, Note, Price, Type, \
    Consultant, Plan, TaskComments, Tasks, Member, Access, Group, CreditInfo, CreditLogs

# Register your models here.
admin.site.register(User)
admin.site.register(Consultant)
admin.site.register(Price)
admin.site.register(Plan)
admin.site.register(Items)
admin.site.register(Group)
admin.site.register(Tasks)
admin.site.register(CreditInfo)
admin.site.register(CreditLogs)
