from decimal import Decimal
from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.generics import GenericAPIView

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from goods.models import SKU
from orders.serializers import OrderSKUSerializer, OrderSettlementSerializer, OrderSerializer


# Create your views here.

# POST /orders/
class OrderView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def post(self, request):
        """
        订单数据保存(订单创建):
        1. 接收参数并进行校验(address是否存在，pay_method是否合法)
        2. 保存订单数据
        3. 返回应答，订单保存成功
        """
        # 1. 接收参数并进行校验(address是否存在，pay_method是否合法)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. 保存订单数据(create)
        serializer.save()

        # 3. 返回应答，订单保存成功
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# GET /orders/settlement/
class OrderSettlementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        获取订单结算的数据:
        1. 从redis获取用户购物车中被勾选的商品id和对应数量count
        2. 根据商品的id获取对应商品的数据 & 订单运费
        3. 将订单结算数据序列化并返回
        """
        # 获取登录user
        user = request.user

        # 1. 从redis获取用户购物车中被勾选的商品id和对应数量count
        redis_conn = get_redis_connection('cart')

        # 从redis set中获取用户购物车被勾选的商品的id
        cart_selected_key = 'cart_selected_%s' % user.id

        # (b'<sku_id>', b'<sku_id>', ...)
        sku_ids = redis_conn.smembers(cart_selected_key)

        # 从redis hash中获取用户购物车中所有商品的id和对应数量count
        cart_key = 'cart_%s' % user.id
        # {
        #     b'<sku_id>': b'<count>',
        #     ...
        # }
        cart_dict = redis_conn.hgetall(cart_key)

        # 组织数据
        # {
        #     '<sku_id>': '<count>',
        #     ...
        # }
        cart = {}

        for sku_id, count in cart_dict.items():
            cart[int(sku_id)] = int(count)

        # 2. 根据商品的id获取对应商品的数据 & 订单运费
        skus = SKU.objects.filter(id__in=sku_ids)

        for sku in skus:
            # 给sku对象增加属性count，保存该商品所要结算的数量
            sku.count = cart[sku.id]

        # 组织运费
        freight = Decimal(10)

        # 3. 将订单结算数据序列化并返回
        res_dict = {
            'freight': freight,
            'skus': skus
        }

        serializer = OrderSettlementSerializer(res_dict)
        return Response(serializer.data)

    def get_1(self, request):
        """
        获取订单结算的数据:
        1. 从redis获取用户购物车中被勾选的商品id和对应数量count
        2. 根据商品的id获取对应商品的数据 & 订单运费
        3. 将订单结算数据序列化并返回
        """
        # 获取登录user
        user = request.user

        # 1. 从redis获取用户购物车中被勾选的商品id和对应数量count
        redis_conn = get_redis_connection('cart')

        # 从redis set中获取用户购物车被勾选的商品的id
        cart_selected_key = 'cart_selected_%s' % user.id

        # (b'<sku_id>', b'<sku_id>', ...)
        sku_ids = redis_conn.smembers(cart_selected_key)

        # 从redis hash中获取用户购物车中所有商品的id和对应数量count
        cart_key = 'cart_%s' % user.id
        # {
        #     b'<sku_id>': b'<count>',
        #     ...
        # }
        cart_dict = redis_conn.hgetall(cart_key)

        # 组织数据
        # {
        #     '<sku_id>': '<count>',
        #     ...
        # }
        cart = {}

        for sku_id, count in cart_dict.items():
            cart[int(sku_id)] = int(count)

        # 2. 根据商品的id获取对应商品的数据 & 订单运费
        skus = SKU.objects.filter(id__in=sku_ids)

        for sku in skus:
            # 给sku对象增加属性count，保存该商品所要结算的数量
            sku.count = cart[sku.id]

        serializer = OrderSKUSerializer(skus, many=True)

        # 组织运费
        freight = Decimal(10)

        # 3. 将订单结算数据序列化并返回
        res_data = {
            'freight': freight,
            'skus': serializer.data
        }

        return Response(res_data)