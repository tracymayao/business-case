from django.test import TestCase
import pickle
import base64
# Create your tests here.

if __name__ == "__main__":
    cookie_cart = 'gAN9cQAoSwF9cQEoWAgAAABzZWxlY3RlZHECiFgFAAAAY291bnRxA0sCdUsDfXEEKGgCiWgDSwF1dS4='

    # cart_data = cookie_cart.encode()
    # print(cart_data)
    #
    # cart_data = base64.b64decode(cart_data)
    # print(cart_data)
    #
    # cart_dict = pickle.loads(cart_data)
    # print(cart_dict)

    # 解析cookie中的购物车数据
    # cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
    cart_dict = pickle.loads(base64.b64decode(cookie_cart))
    print(cart_dict)


# if __name__ == "__main__":
#     # pickle.dumps(obj)：将obj对象转换为bytes字节流；
#     cart_dict = {
#         1: {
#             'count': 2,
#             'selected': True
#         },
#         3: {
#             'count': 1,
#             'selected': False
#         }
#     }
#
#     # cart_data = pickle.dumps(cart_dict) # bytes
#     # print(cart_data)
#     #
#     # cart_data = base64.b64encode(cart_data) # bytes
#     # print(cart_data)
#     #
#     # cart_data = cart_data.decode() # str
#     # print(cart_data)
#
#     # 设置cookie中购物车数据
#     cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
#     print(cart_data)


# if __name__ == "__main__":
#     # pickle.dumps(obj)：将obj对象转换为bytes字节流；
#     # cart_dict = {
#     #     1: {
#     #         'count': 2,
#     #         'selected': True
#     #     },
#     #     3: {
#     #         'count': 1,
#     #         'selected': False
#     #     }
#     # }
#     #
#     # cart_data = pickle.dumps(cart_dict)
#     # print(cart_data)
#
#     # pickle.loads(bytes字节流)：将bytes字节流转换为obj对象。
#     # cart_data = b'\x80\x03}q\x00(K\x01}q\x01(X\x08\x00\x00\x00selectedq\x02\x88X\x05\x00\x00\x00countq\x03K\x02uK\x03}q\x04(h\x02\x89h\x03K\x01uu.'
#     # cart_dict = pickle.loads(cart_data)
#     # print(cart_dict)
