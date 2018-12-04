# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-11-02 07:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PicTest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='', verbose_name='图片')),
            ],
            options={
                'verbose_name_plural': 'FDFS上传图片测试',
                'verbose_name': 'FDFS上传图片测试',
                'db_table': 'tb_pics',
            },
        ),
    ]
