from django.urls import path

from . import views

urlpatterns = [

    path(
        "",
        views.home,
        name="home"
    ),

    path(
        "leaderboard/",
        views.leaderboard,
        name="leaderboard"
    ),
    path(
    "buy/<int:product_id>/",
    views.buy_product,
    name="buy_product"
),
path("login/", views.user_login, name="login"),
path("register/", views.register, name="register"),
path("logout/", views.user_logout, name="logout"),
path(
    "leaderboard/",
    views.leaderboard,
    name="leaderboard"
),
path(
    "deliver/<int:order_id>/",
    views.deliver_order,
    name="deliver_order"
),
path("toggle-debug/", views.toggle_debug, name="toggle_debug"),
path("force/<str:mode>/", views.force_phase, name="force_phase"),
path("refresh-orders/", views.refresh_orders, name="refresh_orders"),
path(
    "achievements/",
    views.achievements,
    name="achievements"
),path("finish-tutorial/", views.finish_tutorial, name="finish_tutorial"),
]