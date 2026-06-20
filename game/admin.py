from django.contrib import admin

from .models import *

admin.site.register(Product)
admin.site.register(Player)
admin.site.register(Event)
admin.site.register(DailyMission)
admin.site.register(Achievement)
# admin.site.register(Shop)
admin.site.register(PlayerAchievement)