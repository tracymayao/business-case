import os

from django.shortcuts import render
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from alipay import AliPay

from orders.models import OrderInfo
from payment.models import Payment
# Create your views here.

# http://www.meiduo.site:8080/pay_success.html?
# charset=utf-8&
# 订单编号
# out_trade_no=201811091447510000000002&
# method=alipay.trade.page.pay.return&
# total_amount=3398.00&
# 签名的字符串
# sign=q62b541iGJ6ZXMing7Pkyv9NF0F9jlyNlry1rcd%2Ffx%2FsJ3TtM9dLx74h83pd9kSFh70TcPTNsDz4v4d26g%2BI4MqhMMO4fimECn%2F0%2BNi1T2SuQSLMAzik0bgQeYQVYw6K9OqPkaD6%2FdJCQ3dO7RnrvwxR8G3Fn%2FpoH361tKawtwxzocCHglefIC4x4Pi1%2F%2BH0B0fj7LqsR07jgipRYxBjE3E50DsO0lVtBx6SUM%2FhdWmecTgkVmy2q3CI%2FkWLXRH45CJeZoSBbusYmXL9jeqPiywdQ9SZNcuZNa2O867Q%2FezP9vUi03nV0uS2%2Bom7VRkntAm3%2BXCB1bIOxUuMkOgwzA%3D%3D&
# 支付交易编号
# trade_no=2018110922001485920500548038&
# auth_app_id=2016090800464054&version=1.0&
# app_id=2016090800464054&
# sign_type=RSA2&
# seller_id=2088102174694091&
# timestamp=2018-11-09+14%3A48%3A49


# PUT /payment/status/?支付结果参数
class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        """
        支付结果数据保存:
        1. 获取支付结果参数并进行签名验证
        2. 校验订单是否有效
        3. 保存支付的结果数据&修改订单支付状态
        4. 返回应答，支付成功
        """
        # 1. 获取支付结果参数并进行签名验证
        data = request.query_params.dict()
        signature = data.pop('sign')

        # 创建Alipay类的对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,  # 开发应用APPID
            app_notify_url=None,  # 默认回调url
            # 网址私钥文件路径
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/app_private_key.pem'),
            # 支付宝公钥文件路径，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                'keys/alipay_public_key.pem'),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 是否使用沙箱环境，默认False
        )

        # 验证签名
        success = alipay.verify(data, signature)

        if not success:
            # 验证失败
            return Response({'message': '非法请求'}, status=status.HTTP_403_FORBIDDEN)

        # 2. 校验订单是否有效
        # 获取订单编号
        order_id = data.get('out_trade_no')
        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=request.user,
                status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'], # 待支付
                pay_method=OrderInfo.PAY_METHODS_ENUM['ALIPAY'], # 支付宝
            )
        except OrderInfo.DoesNotExist:
            return Response({'message': '无效的订单信息'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. 保存支付的结果数据&修改订单支付状态
        # 获取支付交易编号
        trade_id = data.get('trade_no')
        Payment.objects.create(
            order=order,
            trade_id=trade_id
        )

        # 修改订单支付状态
        order.status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] # 待发货
        order.save()

        # 4. 返回应答，支付成功
        return Response({'trade_id': trade_id})


# GET /orders/(?P<order_id>\d+)/payment/
class PaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """
        获取支付网址:
        1. 根据order_id查询订单信息并进行校验
        2. 组织支付宝支付网址和参数
        3. 返回支付宝支付网址
        """
        # 1. 根据order_id查询订单信息并进行校验
        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=request.user,
                status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'], # 待支付
                pay_method=OrderInfo.PAY_METHODS_ENUM['ALIPAY'], # 支付宝
            )
        except OrderInfo.DoesNotExist:
            return Response({'message': '无效的订单信息'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 组织支付宝支付网址和参数
        # 创建Alipay类的对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID, # 开发应用APPID
            app_notify_url=None,  # 默认回调url
            # 网址私钥文件路径
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/app_private_key.pem'),
            # 支付宝公钥文件路径，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/alipay_public_key.pem'),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 是否使用沙箱环境，默认False
        )

        # 组织支付相关参数
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id, # 订单编号
            total_amount=str(order.total_amount), # 订单实付款
            subject='美多商城%s' % order_id, # 订单标题
            return_url="http://www.meiduo.site:8080/pay_success.html",
        )

        # 3. 返回支付宝支付网址
        alipay_url = settings.ALIPAY_URL + '?' + order_string
        return Response({'alipay_url': alipay_url})
