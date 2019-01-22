from rest_framework.pagination import PageNumberPagination


class StandardResultPagination(PageNumberPagination):
    """自定义分页类"""
    # 指定分页的页容量
    page_size = 6
    # 指定获取分页数据传递的页容量参数的名称
    page_size_query_param = 'page_size'
    # 指定最大的页容量
    max_page_size = 20
