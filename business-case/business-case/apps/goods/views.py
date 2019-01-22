from django.shortcuts import render
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import OrderingFilter
from drf_haystack.viewsets import HaystackViewSet

from goods.models import SKU
from goods.serializers import SKUSerializer, SKUIndexSerializer


# Create your views here.


# 编写搜索视图
# /skus/search/?text=<关键字>
class SKUSearchViewSet(HaystackViewSet):
    # 指定索引模型类
    index_models = [SKU]

    # 指定搜索结果序列化时所采用的序列化器类
    # 搜索结果中每个结果对象都包含2个属性:
    # text: 索引字段的内容
    # object: 搜索出模型对象(此处就是商品模型对象)
    serializer_class = SKUIndexSerializer


# GET /categories/(?P<category_id>\d+)/skus/?page=<页码>&page_size=<页容量>&ordering=<排序字段>
class SKUListView(ListAPIView):
    serializer_class = SKUSerializer
    # 指定当前视图所使用的查询集
    # queryset = SKU.objects.filter(category_id=category_id, is_launched=True)

    def get_queryset(self):
        """返回当前视图所使用的查询集"""
        category_id = self.kwargs['category_id']
        return SKU.objects.filter(category_id=category_id, is_launched=True)

    filter_backends = [OrderingFilter]
    # 指定排序字段
    ordering_fields = ('create_time', 'price', 'sales')

    # def get(self, request, category_id):
    #     """
    #     self.kwargs: 保存从url地址中提取的所有命名参数
    #     获取第三级分类ID下SKU商品的列表数据:
    #     1. 根据category_id查询分类SKU商品的数据
    #     2. 将商品的数据序列化并返回
    #     """
    #     # 1. 根据category_id查询分类SKU商品的数据
    #     skus = self.get_queryset()
    #
    #     # 2. 将商品的数据序列化并返回
    #     serializer = self.get_serializer(skus, many=True)
    #     return Response(serializer.data)
