from django.test import TestCase
from itsdangerous import TimedJSONWebSignatureSerializer as TJWSSerializer
from itsdangerous import BadData

# Create your tests here.

# itsdangerous: 进行数据加密和解密
# 安装: pip install itsdangerous

if __name__ == "__main__":
    # 数据加密
    # req_data = {
    #     'openid': 'QKKDKIDK183838lDKDLLI'
    # }
    #
    # # serializer = TJWSSerializer(secret_key='密钥', expires_in='解密有效时间')
    # serializer = TJWSSerializer(secret_key='abc123', expires_in=3600)
    #
    # res_data = serializer.dumps(req_data) # bytes
    # res_str = res_data.decode() # str
    # print(res_str)

    # 数据加密
    # req_data = 'eyJleHAiOjE1NDA3MTk3MjEsImlhdCI6MTU0MDcxNjEyMSwiYWxnIjoiSFMyNTYifQ.eyJvcGVuaWQiOiJRS0tES0lESzE4MzgzOGxES0RMTEkifQ.Ub1wC-VIsL332HcPPHJMnf4ChDBScHMYnI_cPCj-0Yk'
    #
    # serializer = TJWSSerializer(secret_key='abc123')
    #
    # try:
    #     res_data = serializer.loads(req_data)
    # except BadData:
    #     print('解密失败')
    # else:
    #     print(res_data)
    pass




if __name__ == "__main__":
    # 将字典转换为查询字符串
    # from urllib.parse import urlencode
    #
    # req_dict = {
    #     'a': 1,
    #     'b': 2,
    #     'c': 3
    # }
    #
    # res = urlencode(req_dict)
    # print(res)

    # 将查询字符串转换为python字典
    # from urllib.parse import parse_qs
    #
    # req_str = 'a=1&b=2&c=3'
    #
    # res = parse_qs(req_str) # 字典键对应值类型为list
    # print(res)

    # 通过代码发起http请求
    # from urllib.request import urlopen
    #
    # req_url = 'http://api.meiduo.site:8000/mobiles/13155667788/count/'
    #
    # # 此函数会发起http请求并返回一个响应对象
    # response = urlopen(req_url)
    # # 获取响应数据
    # res_data = response.read() # bytes
    #
    # print(res_data)

    pass