from django.shortcuts import render, redirect
from .models import *
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout
import random
from django.contrib.auth.decorators import login_required
from .models import Player
from django.contrib import messages
from collections import defaultdict
from .game_engine import game_tick
from django.contrib.messages import get_messages
def calc_inventory(inv):
    total = 0

    if not isinstance(inv, dict):
        return 0

    for batches in inv.values():

        if isinstance(batches, int):
            total += batches

        elif isinstance(batches, list):
            for b in batches:
                total += b.get("qty", 0)

    return total

def home(request):

    if not request.user.is_authenticated:
        return redirect("login")

    player = Player.objects.get(user=request.user)

    if not player.phase_start:
        player.phase = "buy"
        player.phase_start = timezone.now()
        player.save()

    # 🧪 debug mode 不更新時間
    if not getattr(player, "debug_mode", False):
        update_phase(player)

    # ======================
    # 1. 訂單生成
    # ======================
    if player.phase == "sell":

        ORDER_LIMIT = 8  # 你想要幾張就改這裡

        current = Order.objects.filter(completed=False).count()

        need = ORDER_LIMIT - current

        for _ in range(max(0, need)):
            products = Product.objects.filter(
                unlock_level__lte=player.level
            )

            if not products.exists():
                break

            product = random.choice(list(products))

            qty = random.randint(1, 10)

            Order.objects.create(
                product=product,
                quantity=qty,
                reward=qty * product.price * 3,
                customer_name=random.choice([
                    "小明", "阿強", "AI客戶", "批發商"
                ]),
                snapshot=product.image
            )

    # ======================
    # 2. 商品
    # ======================
    products = Product.objects.filter(
        unlock_level__lte=player.level
    )

    # ======================
    # 3. 訂單
    # ======================
    orders = Order.objects.filter(completed=False)

    # ======================
    # 4. EXP
    # ======================
    next_level_exp = get_need_exp(player.level)
    exp_to_next = next_level_exp - player.exp

    # ======================
    # 5. 時間
    # ======================
    now = timezone.now()

    total_time = 120 if player.phase == "buy" else 180

    remaining = total_time - int(
        (now - player.phase_start).total_seconds()
    )

    remaining = max(0, remaining)

    # ======================
    # 6. 📦 安全 inventory（重點修正）
    # ======================
    inv = player.inventory or {}

    used_capacity = calc_inventory(inv)

    # ======================
    # 7. 📦 使用容量
    # ======================
    # used_capacity = 0

    # for batches in inv.values():

    #     if isinstance(batches, int):
    #         used_capacity += batches
    #     elif isinstance(batches, list):
    #         for batch in batches:
    #             used_capacity += batch.get("qty", 0)

    # ======================
    # 8. 📦 inventory 顯示（修正版）
    # ======================
    inventory_display = []

    for pid, batches in (player.inventory or {}).items():

        total = sum(b.get("qty", 0) for b in batches)

        product = Product.objects.filter(id=pid).first()

        inventory_display.append({
            "name": product.name if product else f"未知商品({pid})",
            "qty": total
        })

    new_achievements = check_achievements(player)

    for a in new_achievements:
        messages.success(
            request,
            f"🏆 成就解鎖：{a['name']} +{a['reward']}金幣"
        )
    
    storage = get_messages(request)

    messages_list = [
        {
            "message": m.message,
            "tags": m.tags
        }
        for m in storage
    ]

    is_dev = request.user.username in ["admin", "11346006"]

    # ======================
    # 9. render
    # ======================
    return render(request, "game/home.html", {
        "player": player,
        "products": products,
        "orders": orders,
        "exp_to_next": exp_to_next,
        "next_level_exp": next_level_exp,
        "remaining": remaining,
        "used_capacity": used_capacity,
        "inventory_display": inventory_display,
        "new_achievements": new_achievements,
        "capacity": get_capacity(player.level),
        "messages_json": messages_list,
        "is_dev": is_dev,
    })

def buy_product(request, product_id):

    player = Player.objects.get(user=request.user)
    product = Product.objects.get(id=product_id)

    quantity = int(request.POST.get("quantity", 1))

    total_cost = product.price * quantity

    if player.money < total_cost:
        messages.error(request, "金錢不足")
        return redirect("home")

    capacity = get_capacity(player.level)

    inv = player.inventory or {}

    # 🔥 統一 key
    pid = str(product.id)

    # 🔥 計算容量（統一）
    used = calc_inventory(inv)

    if used + quantity > capacity:
        messages.error(request, "倉庫已滿")
        return redirect("home")

    # 💰 扣錢
    player.money -= total_cost

    # 📦 寫入 inventory（標準化）
    inv.setdefault(pid, [])

    inv[pid].append({
        "qty": quantity,
        "expire": 120
    })

    player.inventory = inv

    player.exp += 5
    check_level_up(player)
    player.save()

    return redirect("home")

def register(request):

    if request.method == "POST":

        username = request.POST["username"]
        password = request.POST["password"]

        user = User.objects.create_user(
            username=username,
            password=password
        )

        Player.objects.create(
            user=user,
            phase="buy",
            phase_start=timezone.now(),
            day=1,
            money=0,
            exp=0,
        )

        login(request, user)

        return redirect("home")

    return render(request, "game/register.html")

def user_login(request):

    if request.method == "POST":

        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:

            auth_login(request, user)

            return redirect("home")

    return render(request, "game/login.html")


def user_logout(request):

    logout(request)

    return redirect("login")

def get_need_exp(level):
    return int(150 * (level ** 1.6))
def check_level_up(player):

    while True:

        need_exp = get_need_exp(player.level)

        if player.exp < need_exp:
            break

        player.exp -= need_exp
        player.level += 1

    player.save()

def leaderboard(request):

    players = Player.objects.order_by(
        "-money"
    )

    return render(
        request,
        "game/leaderboard.html",
        {
            "players": players
        }
    )




def get_event(player):
    now = timezone.now()

    if not player.last_event_time:
        player.last_event_time = now

    if (now - player.last_event_time).total_seconds() >= 180:
        player.last_event_time = now
        player.save()
        return Event.objects.order_by("?").first()

    return None



def deliver_order(request, order_id):

    player = Player.objects.get(user=request.user)
    order = Order.objects.get(id=order_id)

    inv = player.inventory or {}
    pid = str(order.product.id)

    batches = inv.get(pid, [])

    # 🧯 防呆：統一格式
    if isinstance(batches, int):
        batches = [{"qty": batches, "expire": 999}]
    elif not isinstance(batches, list):
        batches = []

    total = sum(b.get("qty", 0) for b in batches)

    # ❌ 庫存不足
    if total < order.quantity:
        player.reputation -= 10
        player.save()

        messages.error(
            request,
            f"❌ 庫存不足！需要 {order.quantity}，目前只有 {total}"
        )
        return redirect("home")

    remaining = order.quantity
    new_batches = []

    for b in batches:
        qty = b.get("qty", 0)

        if remaining <= 0:
            new_batches.append(b)
            continue

        if qty <= remaining:
            remaining -= qty
            continue
        else:
            b["qty"] = qty - remaining
            remaining = 0
            new_batches.append(b)

    inv[pid] = new_batches
    player.inventory = inv

    # 💰 結算
    player.money += order.reward
    player.exp += order.quantity * 10
    order.completed = True

    check_level_up(player)

    player.save()
    order.save()

    messages.success(
    request,
    f"📦 出貨成功 {order.product.name} x{order.quantity}"
    )

    return redirect("home")
def update_phase(player):

    now = timezone.now()

    if not player.phase_start:
        player.phase_start = now
        player.phase = "buy"
        player.save()
        return

    elapsed = (now - player.phase_start).total_seconds()

    BUY_TIME = 120
    SELL_TIME = 180

    if player.phase == "buy":

        if elapsed >= BUY_TIME:
            player.phase = "sell"
            player.phase_start = now
            player.save()

    elif player.phase == "sell":

        if elapsed >= SELL_TIME:
            player.phase = "buy"
            player.phase_start = now
            player.day += 1
            player.save()
            
def toggle_debug(request):
    player = Player.objects.get(user=request.user)

    player.debug_mode = not player.debug_mode
    player.save()

    return redirect("home")

def force_phase(request, mode):
    player = Player.objects.get(user=request.user)

    if player.debug_mode:
        if mode in ["buy", "sell"]:
            player.phase = mode
            player.phase_start = timezone.now()
            player.save()

    return redirect("home")


def ai_select_product(player, event=None):

    products = Product.objects.filter(
        unlock_level__lte=player.level
    )

    weighted = []

    for p in products:

        weight = max(1, 10 - (p.unlock_level - player.level))

        # 💰 價格影響
        if p.price < 50:
            weight += 2

        # 🌍 事件影響
        if event:

            if event.effect_type == "rain" and "雨" in p.name:
                weight *= event.multiplier

            if event.effect_type == "heat" and "飲料" in p.name:
                weight *= event.multiplier

        weighted.append((p, int(weight)))

    pool = [p for p, w in weighted for _ in range(w)]

    return random.choice(pool) if pool else None
def generate_order(player):

    event = get_active_event()

    if Order.objects.filter(completed=False).count() < 5:

        product = ai_select_product(player, event)

        if not product:
            return

        qty = random.randint(1, min(10, player.level + 3))

        reward = int(
            qty * product.price * random.uniform(2.0, 3.5)
        )

        Order.objects.create(
            product=product,
            quantity=qty,
            reward=reward,
            customer_name=random.choice([
                "AI客戶", "批發商", "便利商店", "企業訂單"
            ]),
            snapshot=product.image
        )

def get_active_event():
    return Event.objects.filter(active=True).first()


def get_hot_products():

    hot = defaultdict(int)

    orders = Order.objects.filter(completed=True)

    for o in orders:
        hot[o.product] += o.quantity

    result = sorted(
        hot.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return result[:5]


def check_achievements(player):

    unlocked = set(
        PlayerAchievement.objects.filter(
            player=player
        ).values_list(
            "achievement__name",
            flat=True
        )
    )

    new_unlocks = []

    achievements = [

        ("第一天營業",
         player.day >= 1,
         100),

        ("營業一週",
         player.day >= 7,
         500),

        ("營業一個月",
         player.day >= 30,
         2000),

        ("第一桶金",
         player.money >= 1000,
         200),

        ("小富翁",
         player.money >= 10000,
         1000),

        ("大富翁",
         player.money >= 100000,
         5000),

        ("第一次出貨",
         player.total_orders >= 1,
         150),

        ("出貨達人",
         player.total_orders >= 100,
         1000),

        ("物流中心",
         player.total_orders >= 1000,
         5000),

        ("新手店長",
         player.level >= 5,
         500),

        ("資深店長",
         player.level >= 10,
         2000),

        ("傳奇店長",
         player.level >= 20,
         10000),
    ]

    for name, condition, reward in achievements:

        if condition and name not in unlocked:

            ach, _ = Achievement.objects.get_or_create(
                name=name,
                defaults={
                    "reward": reward
                }
            )

            PlayerAchievement.objects.create(
                player=player,
                achievement=ach
            )

            player.money += reward

            new_unlocks.append({
                "name": name,
                "reward": reward
            })

    player.save()

    return new_unlocks


def refresh_orders(request):


    player = Player.objects.get(user=request.user)

    # 💰 刷新費用
    refresh_cost = 50

    # ❌ 錢不夠
    if player.money < refresh_cost:
        messages.error(request, "金錢不足，無法刷新訂單")
        return redirect("home")

    # 💸 扣錢
    player.money -= refresh_cost
    player.save()

    # 🧹 刪除未完成訂單
    Order.objects.filter(completed=False).delete()

    # 🤖 重新生成訂單（5筆）
    for _ in range(5):

        products = Product.objects.filter(
            unlock_level__lte=player.level
        )

        if not products.exists():
            break

        product = random.choice(list(products))

        qty = random.randint(1, 10)

        reward = int(qty * product.price * random.uniform(2.0, 3.5))

        Order.objects.create(
            product=product,
            quantity=qty,
            reward=reward,
            customer_name=random.choice([
                "小明", "阿強", "AI客戶", "批發商", "企業訂單"
            ]),
            snapshot=product.image
        )

    messages.success(request, "已刷新訂單（消耗 50 金幣）")
    return redirect("home")

def get_capacity(level):
    return 50 + (level * 20)



def achievements(request):

    player = Player.objects.get(user=request.user)

    unlocked = set(
        PlayerAchievement.objects.filter(
            player=player
        ).values_list(
            "achievement__name",
            flat=True
        )
    )

    all_achievements = [

        ("第一天營業", "成功經營一天"),
        ("營業一週", "成功經營7天"),
        ("營業一個月", "成功經營30天"),

        ("第一桶金", "持有1000金幣"),
        ("小富翁", "持有10000金幣"),
        ("大富翁", "持有100000金幣"),

        ("第一次出貨", "完成第一次訂單"),
        ("出貨達人", "完成100次訂單"),
        ("物流中心", "完成1000次訂單"),

        ("新手店長", "達到5級"),
        ("資深店長", "達到10級"),
        ("傳奇店長", "達到20級"),
    ]

    achievement_list = []

    for name, desc in all_achievements:

        achievement_list.append({
            "name": name,
            "desc": desc,
            "unlocked": name in unlocked
        })

    return render(
        request,
        "game/achievements.html",
        {
            "achievement_list": achievement_list
        }
    )





