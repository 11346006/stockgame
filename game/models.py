from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


# =========================
# 📦 商品
# =========================
class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField(default=0)

    image = models.CharField(
        max_length=100,
        default="images/default.png"
    )

    unlock_level = models.IntegerField(default=1)


# =========================
# 👤 玩家
# =========================
class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    money = models.IntegerField(default=1000)
    level = models.IntegerField(default=1)
    exp = models.IntegerField(default=0)

    day = models.IntegerField(default=1)

    # 🟡 遊戲階段（買 / 賣）
    phase = models.CharField(max_length=20, default="buy")
    phase_start = models.DateTimeField(default=timezone.now)

    reputation = models.IntegerField(default=100)

    # ⭐ NEW：玩家倉庫
    inventory = models.JSONField(default=dict)
    debug_mode = models.BooleanField(default=False)
    total_orders = models.IntegerField(default=0)

    total_sales = models.IntegerField(default=0)

    total_profit = models.IntegerField(default=0)
    def __str__(self):
        return self.user.username


# =========================
# 📣 市場事件
# =========================
class Event(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()

    # 影響類型：rain / heat / normal
    effect_type = models.CharField(max_length=20, default="normal")

    # 影響倍率
    multiplier = models.FloatField(default=1.0)

    active = models.BooleanField(default=True)


# =========================
# 🎯 每日任務
# =========================
class DailyMission(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()

    reward = models.IntegerField(default=100)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title


# =========================
# 🏆 成就
# =========================
class Achievement(models.Model):
    name = models.CharField(max_length=100)
    condition = models.CharField(
        max_length=100,
        default="none"
    )
    reward = models.IntegerField(default=100)


# =========================
# 🏅 玩家成就
# =========================
class PlayerAchievement(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)


# =========================
# 📦 訂單
# =========================
class Order(models.Model):
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.IntegerField()
    reward = models.IntegerField()

    completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    customer_name = models.CharField(max_length=100, default="匿名")

    snapshot = models.ImageField(
        upload_to="orders/",
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"