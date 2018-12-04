import re

from users.models import User


def jwt_response_payload_handler(token, user=None, request=None):
    """自定义jwt扩展登录视图响应数函数"""
    return {
        'user_id': user.id,
        'username': user.username,
        'token': token
    }


# 自定义Django的认证后端类
from django.contrib.auth.backends import ModelBackend


def get_user_by_account(account):
    """
    account: 可能为用户名或手机号
    """
    try:
        if re.match(r'^1[3-9]\d{9}$', account):
            # 根据手机号查询账户
            user = User.objects.get(mobile=account)
        else:
            # 根据用户名查询账户
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user


class UsernameMobileAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        username: 接收账户，可能为用户名或手机号
        password: 账户密码
        """
        # 根据用户名或手机号查询账户信息
        user = get_user_by_account(username)

        # 校验账户密码是否正确
        if user and user.check_password(password):
            return user
