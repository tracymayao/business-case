import re

from django.core.mail import send_mail
from django.conf import settings
from django_redis import get_redis_connection
from rest_framework import serializers

from goods.models import SKU
from users import constants
from users.models import User, Address


class BrowseHistorySerializer(serializers.Serializer):
    """历史浏览的序列化器类"""
    sku_id = serializers.IntegerField(label='商品SKU编号', min_value=1)

    def validate_sku_id(self, value):
        """sku_id对应商品是否存在"""
        try:
            sku = SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError('商品不存在')

        return value

    def create(self, validated_data):
        """在redis中存储用户浏览商品的sku_id"""
        # 获取登录用户user
        user = self.context['request'].user

        # 获取redis链接
        redis_conn = get_redis_connection('histories') # StrictRedis
        # 创建管道对象
        pl = redis_conn.pipeline()

        history_key = 'history_%s' % user.id

        sku_id = validated_data['sku_id']

        # 去重：如果用户已经浏览过该商品，需要将商品id从redis列表中移除。
        pl.lrem(history_key, 0, sku_id)

        # 左侧加入: 保持用户浏览顺序。
        pl.lpush(history_key, sku_id)

        # 截取: 只保留最新的几个浏览记录。
        pl.ltrim(history_key, 0, constants.USER_BROWSING_HISTORY_COUNTS_LIMIT - 1)

        # 一次性执行管道中的所有命令
        pl.execute()

        return validated_data


class UserAddressSerializer(serializers.ModelSerializer):
    """
    用户地址序列化器
    """
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label='省ID', required=True)
    city_id = serializers.IntegerField(label='市ID', required=True)
    district_id = serializers.IntegerField(label='区ID', required=True)

    class Meta:
        model = Address
        exclude = ('user', 'is_deleted', 'create_time', 'update_time')

    def validate_mobile(self, value):
        """
        验证手机号
        """
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def create(self, validated_data):
        """
        保存
        """
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    """
    地址标题
    """
    class Meta:
        model = Address
        fields = ('title',)


class EmailSerializer(serializers.ModelSerializer):
    """邮箱序列化器类"""
    class Meta:
        model = User
        fields = ('id', 'email')

    def update(self, instance, validated_data):
        """设置登录用户的邮箱并给邮箱发送一封验证邮件"""
        # 设置登录用户的邮箱
        email = validated_data['email']
        instance.email = email
        instance.save()


        # 生成邮件验证链接地址: http://www.meiduo.site:8080/success_verify_email.html?user_id=<user_id>
        # 如果直接将用户信息放在链接地址中，可能会造成其他恶意访问
        # 可以将用户信息进行加密，然后将加密的内容放在验证链接地址中
        # 邮件验证链接地址: http://www.meiduo.site:8080/success_verify_email.html?token=<加密内容>
        verify_url = instance.generate_verify_email_url()

        # 发出给`email`邮箱发送验证邮件任务消息
        from celery_tasks.email.tasks import send_verify_email
        send_verify_email.delay(email, verify_url)

        return instance


class UserDetailSerializer(serializers.ModelSerializer):
    """用户序列化器类"""
    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'email', 'email_active')


class UserSerializer(serializers.ModelSerializer):
    """用户注册序列化器类"""
    password2 = serializers.CharField(label='重复密码', write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='同意协议', write_only=True)
    token = serializers.CharField(label='jwt token', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'password2', 'mobile', 'sms_code', 'allow', 'token')

        extra_kwargs = {
            'username': {
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名',
                }
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

    def validate_mobile(self, value):
        """手机号格式，手机号是否注册"""
        # 手机号格式
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式不正确')

        # 手机号是否注册
        res = User.objects.filter(mobile=value).count()

        if res > 0:
            raise serializers.ValidationError('手机号已注册')

        return value

    def validate_allow(self, value):
        """是否同意协议"""
        # 是否同意协议
        if value != 'true':
            raise serializers.ValidationError('请同意协议')

        return value

    def validate(self, attrs):
        """两次密码是否一致，短信验证码是否正确"""
        # 两次密码是否一致
        password = attrs['password']
        password2 = attrs['password2']

        if password != password2:
            raise serializers.ValidationError('两次密码不一致')

        # 短信验证码是否正确
        mobile = attrs['mobile']

        # 从redis中获取真实的短信验证码文本
        redis_conn = get_redis_connection('verify_codes')
        # bytes
        real_sms_code = redis_conn.get('sms_%s' % mobile) # None

        if real_sms_code is None:
            raise serializers.ValidationError('短信验证码已过期')

        # 对比短信验证码
        sms_code = attrs['sms_code'] # str

        if sms_code != real_sms_code.decode():
            raise serializers.ValidationError('短信验证码错误')

        return attrs

    def create(self, validated_data):
        """创建新用户并保存注册用户的信息"""
        # 清除无用的数据
        del validated_data['password2']
        del validated_data['sms_code']
        del validated_data['allow']

        # 创建新用户并保存注册用户的信息
        user = User.objects.create_user(**validated_data)

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

        # 返回user
        return user


