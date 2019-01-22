from datetime import datetime

from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import mixins
from rest_framework import status
from rest_framework.decorators import action

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView, CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import ObtainJSONWebToken, jwt_response_payload_handler

from cart.utils import merge_cookie_cart_to_redis
from goods.models import SKU
from goods.serializers import SKUSerializer
from users import constants
from users import serializers
from users.models import User
from users.serializers import UserSerializer, UserDetailSerializer, EmailSerializer, BrowseHistorySerializer


# Create your views here.
# POST /authorizations/
class UserAuthorizeView(ObtainJSONWebToken):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            response_data = jwt_response_payload_handler(token, user, request)
            response = Response(response_data)
            if api_settings.JWT_AUTH_COOKIE:
                expiration = (datetime.utcnow() +
                              api_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                    token,
                                    expires=expiration,
                                    httponly=True)
            # 调用合并购物车记录的函数
            merge_cookie_cart_to_redis(request, user, response)

            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# POST /browse_histories/
class BrowseHistoryView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BrowseHistorySerializer

    def get(self, request):
        """
        登录用户浏览记录获取:
        1. 从redis中获取用户的浏览的商品sku_id
        2. 根据sku_id获取对应商品的数据
        3. 将商品数据序列化并返回
        """
        # 获取登录用户
        user = request.user

        # 1. 从redis中获取用户的浏览的商品sku_id
        redis_conn = get_redis_connection('histories')
        history_key = 'history_%s' % user.id

        # [b'<sku_id>', b'<sku_id>', ...]
        sku_ids = redis_conn.lrange(history_key, 0, -1)

        # 2. 根据sku_id获取对应商品的数据
        skus = []

        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            skus.append(sku)

        # 3. 将商品数据序列化并返回
        serializer = SKUSerializer(skus, many=True)
        return Response(serializer.data)

    # def post(self, request):
    #     """
    #     登录用户的浏览记录添加:
    #     1. 获取商品sku_id并校验(sku_id必传，sku_id对应商品是否存在)
    #     2. 在redis中存储用户浏览商品的sku_id
    #     3. 返回应答，浏览记录保存成功
    #     """
    #     # 1. 获取商品sku_id并校验(sku_id必传，sku_id对应商品是否存在)
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #
    #     # 2. 在redis中存储用户浏览商品的sku_id(create)
    #     serializer.save()
    #
    #     # 3. 返回应答，浏览记录保存成功
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)


class AddressViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, GenericViewSet):
    """
    用户地址新增与修改
    """
    serializer_class = serializers.UserAddressSerializer
    permissions = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    # GET /addresses/
    def list(self, request, *args, **kwargs):
        """
        用户地址列表数据
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data,
        })

    # POST /addresses/
    def create(self, request, *args, **kwargs):
        """
        保存用户地址数据
        """
        # 检查用户地址数据数目不能超过上限
        count = request.user.addresses.filter(is_deleted=False).count()
        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({'message': '保存地址数据已达到上限'}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    # delete /addresses/<pk>/
    def destroy(self, request, *args, **kwargs):
        """
        处理删除
        """
        address = self.get_object()

        # 进行逻辑删除
        address.is_deleted = True
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    # put /addresses/pk/status/
    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """
        设置默认地址
        """
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)

    # put /addresses/pk/title/
    # 需要请求体参数 title
    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """
        修改标题
        """
        address = self.get_object()
        serializer = serializers.AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# PUT /emails/verification/?token=<token>
class EmailVerifyView(APIView):
    def put(self, request):
        """
        用户邮箱验证的API:
        1. 获取token并进行校验(token必传，token是否有效)
        2. 设置对应用户的邮箱验证标记email_active
        3. 返回应答，邮箱验证成功
        """
        # 1. 获取token并进行校验(token必传，token是否有效)
        token = request.query_params.get('token')

        if token is None:
            return Response({'message': '缺少token参数'}, status=status.HTTP_400_BAD_REQUEST)

        # token是否有效
        user = User.check_verify_email_token(token)

        if user is None:
            return Response({'message': '无效的token数据'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 设置对应用户的邮箱验证标记email_active
        user.email_active = True
        user.save()

        # 3. 返回应答，邮箱验证成功
        return Response({'message': 'OK'})


# PUT /email/
# class EmailView(GenericAPIView):
class EmailView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmailSerializer

    def get_object(self):
        """返回当前登录user"""
        return self.request.user

    # def put(self, request):
    #     """
    #     登录用户的邮箱设置:
    #     1. 获取登录用户user
    #     2. 获取email并校验(email必传，email格式)
    #     3. 设置登录用户的邮箱并给邮箱发送一封验证邮件
    #     4. 返回应答，邮箱设置成功
    #     """
    #     # 1. 获取登录用户user
    #     user = self.get_object()
    #
    #     # 2. 获取email并校验(email必传，email格式)
    #     serializer = self.get_serializer(user, data=request.data)
    #     serializer.is_valid(raise_exeception=True)
    #
    #     # 3. 设置登录用户的邮箱并给邮箱发送一封验证邮件
    #     serializer.save() # update
    #
    #     # 4. 返回应答，邮箱设置成功
    #     return Response(serializer.data)


# GET /user/
# class UserDetailView(GenericAPIView):
class UserDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailSerializer

    def get_object(self):
        """返回当前登录user用户"""
        return self.request.user

    # def get(self, request):
    #     """
    #     self.request: request请求对象
    #     获取登录用户基本信息:
    #     1. 获取登录用户user
    #     2. 将用户数据序列化并返回
    #     """
    #     # 1. 获取登录用户user
    #     user = self.get_object()
    #
    #     # 2. 将用户数据序列化并返回
    #     serializer = self.get_serializer(user)
    #     return Response(serializer.data)


# POST /users/
# class UserView(GenericAPIView):
class UserView(CreateAPIView):
    # 指定当前视图所使用的序列化器类
    serializer_class = UserSerializer

    # def post(self, request):
    #     """
    #     注册用户信息的保存:
    #     1. 接收参数并进行校验(参数完整性，两次密码是否一致，手机号格式，手机号是否注册，短信验证码是否正确，是否同意协议)
    #     2. 创建新用户并保存注册用户的信息
    #     3. 返回应答，注册成功
    #     """
    #     # 1. 接收参数并进行校验(参数完整性，两次密码是否一致，手机号格式，手机号是否注册，短信验证码是否正确，是否同意协议)
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #
    #     # 2. 创建新用户并保存注册用户的信息(create)
    #     serializer.save()
    #
    #     # 3. 返回应答，注册成功
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)


# url(r'^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
class UsernameCountView(APIView):
    """
    用户名数量
    """
    def get(self, request, username):
        """
        获取指定用户名数量
        """
        count = User.objects.filter(username=username).count()

        data = {
            'username': username,
            'count': count
        }

        return Response(data)


# url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
class MobileCountView(APIView):
    """
    手机号数量
    """
    def get(self, request, mobile):
        """
        获取指定手机号数量
        """
        count = User.objects.filter(mobile=mobile).count()

        data = {
            'mobile': mobile,
            'count': count
        }

        return Response(data)