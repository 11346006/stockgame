from django.utils import timezone
from game.models import Product, Player

def tick(player):
    now = timezone.now()

    elapsed = (now - player.last_update).total_seconds()

    if elapsed < 10:
        return player, 0

    cycles = int(elapsed // 10)

    total_money = 0
    total_exp = 0

    products = Product.objects.all()

    for p in products:
        sold = min(p.stock, p.sell_per_min * cycles)

        p.stock -= sold

        income = sold * p.price * 2

        total_money += income
        total_exp += sold

        p.save()

    player.money += total_money
    player.exp += total_exp

    # 升級
    while player.exp >= player.level * 100:
        player.exp -= player.level * 100
        player.level += 1

    player.last_update = now
    player.save()

    return player, total_money