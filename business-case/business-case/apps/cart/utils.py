import base64
import pickle

from django_redis import get_redis_connection


def merge_cookie_cart_to_redis(request, user, response):
    """合并cookie购物车记录到redis数据库"""
    # 获取cookie中的购物车记录
    cookie_cart = request.COOKIES.get('cart') # None

    if cookie_cart is None:
        # cookie购物车无数据
        return

    # 解析cookie中的购物车数据
    # {
    #     '<sku_id>': {
    #         'count': '<count>',
    #         'selected': '<selected>'
    #     },
    #     ...
    # }
    cart_dict = pickle.loads(base64.b64decode(cookie_cart)) # {}

    if not cookie_cart:
        # 字典为空，cookie购物车无数据
        return

    # 组织数据
    # 保存cookie购物车记录中所有商品的id和对应数量count，此数据在进行合并时需要添加到redis hash元素中
    # {
    #     '<sku_id>': '<count>',
    #     ...
    # }
    cart = {}

    # 保存cookie购物车记录中被勾选的商品的id，此数据在进行合并时需要添加的redis set元素中
    redis_selected_add = []

    # 保存cookie购物车记录中未被勾选的商品的id，此数据在进行合并时需要从redis set元素移除
    redis_selected_remove = []

    for sku_id, count_selected in cart_dict.items():
        cart[sku_id] = count_selected['count']

        if count_selected['selected']:
            # 勾选
            redis_selected_add.append(sku_id)
        else:
            # 未勾选
            redis_selected_remove.append(sku_id)

    # 进行合并
    redis_conn = get_redis_connection('cart')

    # 将`cart`字典中的key和value作为属性和值添加到redis hash元素中
    cart_key = 'cart_%s' % user.id

    # hmset(key, dict): 将字典中的key和value作为属性和值添加到redis hash元素中，如果属性已存在，会对值进行覆盖
    redis_conn.hmset(cart_key, cart)

    cart_selected_key = 'cart_selected_%s' % user.id
    # 将`redis_selected_add`中所有商品的id添加到redis set元素中
    if redis_selected_add:
        redis_conn.sadd(cart_selected_key, *redis_selected_add)

    # 将`redis_selected_remove`中所有商品的id从redis set元素移除
    if redis_selected_remove:
        redis_conn.srem(cart_selected_key, *redis_selected_remove)

    # 清除cookie中购物车
    response.delete_cookie('cart')











