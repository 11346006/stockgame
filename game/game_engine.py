import random
from collections import defaultdict
from django.utils import timezone
from .models import *


def get_need_exp(level):
    return int(150 * (level ** 1.6))


def get_capacity(level):
    return 50 + level * 20
    
def add_exp(player, amount):

    player.exp += amount

    while True:
        need = get_need_exp(player.level)

        if player.exp < need:
            break

        player.exp -= need
        player.level += 1


def calc_used_capacity(inv):

    used = 0

    for batches in (inv or {}).values():

        if isinstance(batches, int):
            used += batches

        elif isinstance(batches, list):
            for b in batches:
                used += b.get("qty", 0)

    return used
def buy_item(player, product, quantity):

    total_cost = product.price * quantity

    if player.money < total_cost:
        return False, "金錢不足"

    inv = player.inventory or {}

    used = calc_used_capacity(inv)
    cap = get_capacity(player.level)

    if used + quantity > cap:
        return False, "倉庫已滿"

    player.money -= total_cost
    product.stock -= quantity

    pid = str(product.id)

    if pid not in inv:
        inv[pid] = []

    inv[pid].append({
        "qty": quantity,
        "expire": 120
    })

    player.inventory = inv

    add_exp(player, 5)

    player.save()
    product.save()

    return True, "購買成功"

def deliver_order(player, order):

    inv = player.inventory or {}
    pid = str(order.product.id)

    batches = inv.get(pid, [])

    if isinstance(batches, int):
        batches = [{"qty": batches}]

    remaining = order.quantity
    new_batches = []

    for b in batches:

        if remaining <= 0:
            new_batches.append(b)
            continue

        if b["qty"] <= remaining:
            remaining -= b["qty"]
            continue
        else:
            b["qty"] -= remaining
            remaining = 0
            new_batches.append(b)

    if remaining > 0:
        player.reputation -= 10
        player.save()
        return False, "庫存不足"

    inv[pid] = new_batches
    player.inventory = inv

    player.money += order.reward
    add_exp(player, order.quantity * 10)

    order.completed = True

    player.save()
    order.save()

    return True, "出貨成功"
def check_achievements(player):

    unlocked = set(
        PlayerAchievement.objects.filter(player=player)
        .values_list("achievement__name", flat=True)
    )

    new = []

    def unlock(name, condition, reward=100):

        if condition and name not in unlocked:

            ach, _ = Achievement.objects.get_or_create(
                name=name,
                defaults={"reward": reward}
            )

            PlayerAchievement.objects.create(
                player=player,
                achievement=ach
            )

            player.money += reward
            new.append(name)

    unlock("第一桶金", player.money >= 1000, 200)
    unlock("第一次出貨", Order.objects.filter(completed=True).exists(), 150)
    unlock("第一天營業", player.day >= 1, 100)

    player.save()

    return new
def generate_orders(player, limit=5):

    if Order.objects.filter(completed=False).count() >= limit:
        return

    products = Product.objects.filter(
        unlock_level__lte=player.level
    )

    if not products.exists():
        return

    product = random.choice(list(products))
    qty = random.randint(1, 10)

    Order.objects.create(
        product=product,
        quantity=qty,
        reward=int(qty * product.price * 3),
        customer_name="AI客戶",
        snapshot=product.image
    )
def game_tick(player, action=None, product=None, quantity=0, order=None):

    # 📦 訂單生成
    generate_orders(player)

    # 🏆 成就
    new_achievements = check_achievements(player)

    result = None

    # 🛒 動作
    if action == "buy":
        result = buy_item(player, product, quantity)

    elif action == "deliver":
        result = deliver_order(player, order)

    player.save()

    return {
        "result": result,
        "achievements": new_achievements
    }




