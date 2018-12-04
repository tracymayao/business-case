from django.http import Http404
from django.shortcuts import render
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.cache.mixins import CacheResponseMixin

from areas.models import Area
from areas.serializers import AreaSerializer, SubAreaSerializer


# Create your views here.

class AreaViewSet(CacheResponseMixin, ReadOnlyModelViewSet):
    """地区视图集"""
    # 关闭当前视图的分页
    pagination_class = None

    def get_serializer_class(self):
        """返回当前视图所使用序列化器类"""
        if self.action == 'list':
            return AreaSerializer
        else:
            return SubAreaSerializer

    def get_queryset(self):
        """返回当前视图所使用的查询集"""
        if self.action == 'list':
            return Area.objects.filter(parent=None)
        else:
            return Area.objects.all()


# GET /areas/(?P<pk>\d+)/
# class SubAreasView(GenericAPIView):
class SubAreasView(RetrieveAPIView):
    serializer_class = SubAreaSerializer
    queryset = Area.objects.all()

    # def get(self, request, pk):
    #     """
    #     获取指定地区的信息(将该地区的下级地区进行嵌套序列化)
    #     1. 根据pk获取指定的地区
    #     2. 将地区进行序列化并返回
    #     """
    #     # 1. 根据pk获取指定的地区
    #     area = self.get_object()
    #
    #     # 2. 将地区进行序列化并返回
    #     serializer = self.get_serializer(area)
    #     return Response(serializer.data)


# GET /areas/
# class AreasView(GenericAPIView):
class AreasView(ListAPIView):
    serializer_class = AreaSerializer
    # 指定当前视图所使用的查询集(此处设置为所有省级地区的信息)
    queryset = Area.objects.filter(parent=None)

    # def get(self, request):
    #     """
    #     获取所有省级地区的信息:
    #     1. 查询所有省级的数据
    #     2. 将省级地区的数据序列化并返回
    #     """
    #     # 1. 查询所有省级的数据
    #     areas = self.get_queryset()
    #
    #     # 2. 将省级地区的数据序列化并返回
    #     serializer = self.get_serializer(areas, many=True)
    #     return Response(serializer.data)
