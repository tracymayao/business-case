import base64
import os

from django_redis import get_redis_connection
from rest_framework import serializers

from oauth.models import OAuthQQUser
from oauth.utils import OAuthQQ
from users.models import User


class QQAuthUserSerializer(serializers.ModelSerializer):
    """QQ登录用户序列化器类"""
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$', write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    access_token = serializers.CharField(label='加密OpenID', write_only=True)
    token = serializers.CharField(label='JWT Token', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'password', 'sms_code', 'access_token', 'token')

        extra_kwargs = {
            'username': {
                'read_only': True,
            },
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

    def validate(self, attrs):
        """短信验证码正确性，access_token是否有效"""
        # access_token是否有效
        access_token = attrs['access_token']

        openid = OAuthQQ.check_save_user_token(access_token)

        if openid is None:
            raise serializers.ValidationError('无效的access_token')

        attrs['openid'] = openid

        # 短信验证码是否正确
        mobile = attrs['mobile']

        # 从redis中获取真实的短信验证码文本
        redis_conn = get_redis_connection('verify_codes')
        # bytes
        real_sms_code = redis_conn.get('sms_%s' % mobile)  # None

        if real_sms_code is None:
            raise serializers.ValidationError('短信验证码已过期')

        # 对比短信验证码
        sms_code = attrs['sms_code']  # str

        if sms_code != real_sms_code.decode():
            raise serializers.ValidationError('短信验证码错误')

        # 如果`mobile`已注册，需要检验密码是否正确
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 用户未注册
            user = None
        else:
            # 已注册，校验对应用户的密码
            password = attrs['password']
            if not user.check_password(password):
                raise serializers.ValidationError('密码错误')

        # 向attrs字典中加入user，以便在进行绑定时直接使用
        attrs['user'] = user

        return attrs

    def create(self, validated_data):
        """保存绑定QQ登录用户信息"""
        # 获取user
        user = validated_data['user']

        if user is None:
            # `mobile`未注册，先创建新用户
            # 随机生成用户名
            username = base64.b64encode(os.urandom(9)).decode()
            password = validated_data['password']
            mobile = validated_data['mobile']
            user = User.objects.create_user(username=username, password=password, mobile=mobile)

        # 获取类视图的对象，给类视图对象增加属性user，用来保存绑定用户对象
        # 以便在类视图中可以直接通过`self.user`获取绑定用户对象
        self.context['view'].user = user

        # 保存QQ登录用户的绑定数据
        openid = validated_data['openid']
        OAuthQQUser.objects.create(
            user=user,
            openid=openid
        )

        # 由服务器生成一个jwt token，保存当前用户的身份信息
        from rest_framework_jwt.settings import api_settings

        # 组织payload数据的方法
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        # 生成jwt token数据的方法
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        # 组织payload数据
        payload = jwt_payload_handler(user)
        # 生成jwt token
        token = jwt_encode_handler(payload)

        # 给user对象增加属性token，保存生成jwt token数据
        user.token = token

        return user
