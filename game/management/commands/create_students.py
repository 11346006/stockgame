from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from game.models import Player


class Command(BaseCommand):
    help = "建立學生帳號"

    def handle(self, *args, **kwargs):

        for i in range(1, 38):

            username = f"113460{i:02d}"

            if User.objects.filter(username=username).exists():
                self.stdout.write(f"{username} 已存在")
                continue

            user = User.objects.create_user(
                username=username,
                password="123456"
            )

            Player.objects.create(user=user)

            self.stdout.write(f"建立成功：{username}")

        self.stdout.write("完成")