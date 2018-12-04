from django.conf import settings
from django.core.files.storage import Storage, FileSystemStorage
from django.utils.deconstruct import deconstructible
from fdfs_client.client import Fdfs_client


@deconstructible
class FDFSStorage(Storage):
    """FDFS文件存储类"""
    def __init__(self, client_conf=None, base_url=None):
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF

        self.client_conf = client_conf

        if base_url is None:
            base_url = settings.FDFS_URL

        self.base_url = base_url

    def _save(self, name, content):
        """
        name: 上传文件名称 1.jpg
        content: 包含上传文件内容的File对象，可以通过content.read()获取上传文件的内容
        """
        client = Fdfs_client(self.client_conf)

        # 上传文件到FDFS文件存储系统
        res = client.upload_by_buffer(content.read())

        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到FDFS系统失败')

        # 获取文件id
        file_id = res.get('Remote file_id')

        return file_id

    def exists(self, name):
        """
        django框架在调用文件存储类中的_save进行文件保存之前，会先调用文件存储类中的exists方法
        判断文件名跟文件存储系统中已有的文件是否冲突
        name: 上传文件名称 1.jpg
        """
        return False

    def url(self, name):
        """
        获取可访问到文件的完整的url地址:
        name: 数据表中存储的文件id
        """
        return self.base_url + name
