import base64
import pickle

from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from cart import constants
from cart.serializers import CartSerializer, CartSKUSerializer, CartDelSerializer, CartSelectAllSerializer
from goods.models import SKU

# Create your views here.


# PUT /cart/selection/
class CartSelectAllView(APIView):
    def perform_authentication(self, request):
        """让当前视图跳过DRF框架的认证过程"""
        pass

    def put(self, request):
        """
        购物车记录全选和全不选:
        1. 获取参数selected并进行校验
        2. 设置用户购物车记录的勾选状态(全选和全不选)
            2.1 如果用户已登录，操作redis中的购物车记录
            2.2 如果用户未登录，操作cookie中的购物车记录
        3. 返回应答，操作成功
        """
        # 1. 获取参数selected并进行校验
        serializer = CartSelectAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取校验之后的内容
        selected = serializer.validated_data['selected']

        try:
            user = request.user
        except Exception as e:
            user = None

        # 2. 设置用户购物车记录的勾选状态(全选和全不选)
        if user is not None and user.is_authenticated:
            # 2.1 如果用户已登录，操作redis中的购物车记录
            redis_conn = get_redis_connection('cart')

            # 从redis hash元素中获取用户购物车添加的所有商品的id
            cart_key = 'cart_%s' % user.id

            # hkeys(key): 获取hash元素中所有是属性
            # [b'<sku_id>', b'<sku_id>', ...]
            sku_ids = redis_conn.hkeys(cart_key)

            cart_selected_key = 'cart_selected_%s' % user.id
            if selected:
                # 全选
                redis_conn.sadd(cart_selected_key, *sku_ids)
            else:
                # 全不选
                redis_conn.srem(cart_selected_key, *sku_ids)

            # 返回应答
            return Response({'message': 'OK'})
        else:
            # 2.2 如果用户未登录，操作cookie中的购物车记录
            # 获取cookie购物车中原始数据
            cookie_cart = request.COOKIES.get('cart')

            if cookie_cart:
                # 解析cookie中的购物车数据
                # {
                #     '<sku_id>': {
                #         'count': '<count>',
                #         'selected': '<selected>'
                #     },
                #     ...
                # }
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}

            # 全选和全不选
            for sku_id in cart_dict:
                cart_dict[sku_id]['selected'] = selected

            # 3. 返回应答，操作成功
            response = Response({'message': 'OK'})
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cart_data, max_age=constants.CART_COOKIE_EXPIRES)
            return response


# POST /cart/
class CartView(APIView):
    def perform_authentication(self, request):
        """让当前视图跳过DRF框架的认证过程"""
        pass

    def delete(self, request):
        """
        购物车记录删除:
        1. 获取参数sku_id并进行校验(sku_id商品是否存在)
        2. 删除购物车记录
            2.1 如果用户已登录，删除redis中对应的购物车记录
            2.2 如果用户未登录，删除cookie中对应的购物车记录
        3. 返回应答，购物车删除添加成功
        """
        # 1. 获取参数sku_id并进行校验(sku_id商品是否存在)
        serializer = CartDelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取校验之后的数据
        sku_id = serializer.validated_data['sku_id']

        # request.user会触发DRF框架的认证过程，但是此处的代码是我们自己调用的，所有自己进行处理
        try:
            user = request.user
        except Exception as e:
            user = None

        # 2. 删除购物车记录
        if user is not None and user.is_authenticated:
            # 2.1 如果用户已登录，删除redis中对应的购物车记录
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()

            # 在redis hash元素中删除对应商品的sku_id和数量count
            cart_key = 'cart_%s' % user.id

            # hdel(key, *fields): 删除hash中指定的属性field和其对应值，有则删除，无则忽略
            pl.hdel(cart_key, sku_id)

            # 在redis set元素中删除商品的勾选状态
            cart_selected_key = 'cart_selected_%s' % user.id

            # srem(key, *members): 从set集合中移除元素，有则移除，无则忽略
            pl.srem(cart_selected_key, sku_id)

            pl.execute()

            # 返回应答
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            response = Response(status=status.HTTP_204_NO_CONTENT)
            # 2.2 如果用户未登录，删除cookie中对应的购物车记录
            # 获取原始cookie的购物车数据
            cookie_cart = request.COOKIES.get('cart') # None

            if cookie_cart is None:
                # 购物车无数据
                return response

            # 解析cookie购物车数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>'
            #     },
            #     ...
            # }
            cart_dict = pickle.loads(base64.b64decode(cookie_cart)) # {}

            if not cart_dict:
                # 字典为空，购物车无数据
                return response

            # 删除cookie购物车数据
            if sku_id in cart_dict:
                del cart_dict[sku_id]
                # 处理cookie购物车数据
                cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
                response.set_cookie('cart', cart_data, max_age=constants.CART_COOKIE_EXPIRES)

            # 3. 返回应答，购物车删除添加成功
            return response

    def put(self, request):
        """
        购物车记录修改:
        1. 获取参数并进行校验(sku_id对应的商品是否存在，商品库存是否足够)
        2. 修改用户的购物车记录
            2.1 如果用户已登录，在redis中修改用户的购物车记录
            2.2 如果用户未登录，在cookie中修改用户的购物车记录
        3. 返回应答，购物车记录修改成功
        """
        # 1. 获取参数并进行校验(sku_id对应的商品是否存在，商品库存是否足够)
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取校验之后的数据
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']

        # request.user会触发DRF框架的认证过程，但是此处的代码是我们自己调用的，所有自己进行处理
        try:
            user = request.user
        except Exception as e:
            user = None

        # 2. 修改用户的购物车记录
        if user is not None and user.is_authenticated:
            # 2.1 如果用户已登录，在redis中修改用户的购物车记录
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()

            # 在redis hash修改用户购物车中对应商品数量count
            cart_key = 'cart_%s' % user.id

            # hset(key, field, value): 设置hash中指定属性field的值为value
            pl.hset(cart_key, sku_id, count)

            # 在redis set修改用户购物车中勾选状态
            cart_selected_key = 'cart_selected_%s' % user.id
            if selected:
                # 勾选
                # sadd(key, *members): 向set集合中添加元素，元素是唯一的
                pl.sadd(cart_selected_key, sku_id)
            else:
                # 取消勾选
                # srem(key, *members): 从set集合中移除元素，有则移除，无则忽略
                pl.srem(cart_selected_key, sku_id)

            pl.execute()

            # 返回响应
            return Response(serializer.data)
        else:
            response = Response(serializer.data)
            # 2.2 如果用户未登录，在cookie中修改用户的购物车记录
            # 获取原始的cookie购物车数据
            cookie_cart = request.COOKIES.get('cart') # None

            if cookie_cart is None:
                # 购物车无数据
                return response

            # 解析cookie购物车数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>'
            #     },
            #     ...
            # }
            cart_dict = pickle.loads(base64.b64decode(cookie_cart)) # {}

            if not cart_dict:
                # 字典为空，购物车无数据
                return response

            # 修改用户的购物车数据
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 3. 返回应答，购物车记录修改成功
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cart_data, max_age=constants.CART_COOKIE_EXPIRES)
            return response

    def get(self, request):
        """
        获取用户的购物车记录:
        1. 获取用户购物车记录
            1.1 如果用户已登录，从redis中获取用户的购物车记录
            1.2 如果用户未登录，从cookie中获取用户的购物车记录
        2. 根据用户购物车中商品的sku_id获取对应商品的数据
        3. 将商品的数据序列化并返回
        """
        try:
            user = request.user
        except Exception as e:
            user = None

        # 1. 获取用户购物车记录
        if user is not None and user.is_authenticated:
            # 1.1 如果用户已登录，从redis中获取用户的购物车记录
            redis_conn = get_redis_connection('cart')

            # 从redis hash中获取登录用户购物车添加的商品的sku_id和对应数量count
            cart_key = 'cart_%s' % user.id
            # hgetall(key): 获取hash中所有的属性和值
            # {
            #     b'<sku_id>': b'<count>',
            #     b'<sku_id>': b'<count>',
            #     ...
            # }
            cart_redis = redis_conn.hgetall(cart_key)

            # 从redis set中获取登录用户购物车记录中被勾选的商品的sku_id
            cart_selected_key = 'cart_selected_%s' % user.id
            # smembers(key): 获取set中所有元素
            # (b'<sku_id>', b'<sku_id>', ...)
            cart_selected_redis = redis_conn.smembers(cart_selected_key)

            # 组织数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>',
            #     },
            #     ...
            # }
            cart_dict = {}

            for sku_id, count in cart_redis.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in cart_selected_redis
                }
        else:
            # 1.2 如果用户未登录，从cookie中获取用户的购物车记录
            # 获取cookie购物车原始数据
            cookie_cart = request.COOKIES.get('cart') # None

            if cookie_cart:
                # 解析cookie中的购物车数据
                # {
                #     '<sku_id>': {
                #         'count': '<count>',
                #         'selected': '<selected>',
                #     },
                #     ...
                # }
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}

        # 2. 根据用户购物车中商品的sku_id获取对应商品的数据
        sku_ids = cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_ids)

        for sku in skus:
            # 给sku对象增加属性count和selected
            # 分别保存当前商品在购物车中添加数量和勾选状态
            sku.count = cart_dict[sku.id]['count']
            sku.selected = cart_dict[sku.id]['selected']

        # 3. 将商品的数据序列化并返回
        serializer = CartSKUSerializer(skus, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        购物车记录添加:
        1. 接收参数并进行校验(sku_id对应的商品是否存在，商品库存是否足够)
        2. 保存用户的购物车记录数据
            2.1 如果用户已登录，在redis中保存用户的购物车记录
            2.2 如果用户未登录，在cookie中保存用户的购物车记录
        3. 返回应答，购物车记录添加成功
        """
        # 1. 接收参数并进行校验(sku_id对应的商品是否存在，商品库存是否足够)
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取校验之后的数据
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']

        # 获取user
        # request.user会触发DRF框架的认证过程，但是此处的代码是我们自己调用的，所有自己进行处理
        try:
            user = request.user
        except Exception as e:
            user = None

        # 2. 保存用户的购物车记录数据
        if user is not None and user.is_authenticated:
            # 2.1 如果用户已登录，在redis中保存用户的购物车记录
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()

            # 在redis hash元素中存储用户添加的商品sku_id和对应数量count
            cart_key = 'cart_%s' % user.id

            # 如果用户的购物车记录中已经添加过该商品，商品的对应数量需要进行累加，否则直接添加新元素
            # hincrby(key, field, count): 给hash中指定属性field的值累加count，如果field不存在，新建属性和值
            pl.hincrby(cart_key, sku_id, count)

            # 在redis set元素中存储用户添加购物车记录时勾选商品sku_id
            cart_selected_key = 'cart_selected_%s' % user.id
            if selected:
                # 勾选
                # sadd(key, *members): 向set集合中添加元素，元素是唯一的
                pl.sadd(cart_selected_key, sku_id)

            pl.execute()

            # 返回应答
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            # 2.2 如果用户未登录，在cookie中保存用户的购物车记录
            # 获取原始的购物车数据
            cookie_cart = request.COOKIES.get('cart') # None

            if cookie_cart:
                # 解析cookie中的购物车数据
                # {
                #     '<sku_id>': {
                #         'count': '<count>',
                #         'selected': '<selected>'
                #     },
                #     ...
                # }
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}

            # 保存用户的购物车数据
            if sku_id in cart_dict:
                # 累加数量
                count += cart_dict[sku_id]['count']

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 3. 返回应答，购物车记录添加成功
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
            # 设置cookie购物车数据
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cart_data, max_age=constants.CART_COOKIE_EXPIRES)
            return response
