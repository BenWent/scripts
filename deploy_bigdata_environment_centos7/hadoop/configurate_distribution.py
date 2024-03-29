#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: ben
# @Date:   2019-07-12 09:21:03
# @Last Modified by:   ben
# @Last Modified time: 2019-07-17 11:20:29
# @Description:        distribute the hadoop environment to each machine in clusters

import os
import socket
import paramiko
import getpass
import commands
from tqdm import tqdm

# 集群中各台机器的root密码
root_password = getpass.getpass('root password: ')

# 获取当前配置的hadoop环境变量
hadoop_home = commands.getoutput('echo ${HADOOP_HOME}')
# hadoop_name = hadoop_home.split('/')[-1]
hadoop_name = os.path.basename(hadoop_home)
hadoop_top_dir = hadoop_home.split('/')[1]  # 注意：linux的根目录是/，所以 [0]是空
hadoop_installation = os.path.dirname(hadoop_home)

# 待上传文件的位置
local_path = '/tmp/{hadoop_name}.tar.gz'.format(hadoop_name=hadoop_name)
# 文件的上传位置（需要指定文件上传后的文件名）
remote_path = '/tmp/{hadoop_name}.tar.gz'.format(hadoop_name=hadoop_name)

# 对配置好的hadoop进行打包
os.system(
    'tar -zcf  {local_path} {hadoop_home}'.format(local_path=local_path, hadoop_home=hadoop_home))

# 获取本机ip
hostname = socket.gethostname()
m_ip = socket.gethostbyname(hostname)

with open('/etc/hosts', mode='r') as file:
    # 设置进度条
    bar = tqdm(list(file), bar_format='{l_bar}{bar}|{n_fmt}/{total_fmt}')

    for line in bar:
        ip_name = line.strip().split()
        # print(ip_name)
        if len(ip_name) != 2:
            continue

        ip = ip_name[0]

        if ip == m_ip:
            continue

        # 设置进度条提示
        bar.set_description('distributing to {ip}'.format(ip=ip))

        # 创建ssh对象
        ssh = paramiko.SSHClient()
        # 允许连接不在know_hosts文件中的主机
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # 连接服务器
        ssh.connect(hostname=ip, port=22, username='root',
                    password=root_password)

        # 将配置好的hadoop发送到slave机器
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)

        # 删除原来的配置
        _, stdout, _ = ssh.exec_command(
            'rm -fr {hadoop_home}'.format(hadoop_home=hadoop_home))
        stdout.channel.recv_exit_status()

        # 解压缩
        stdin, stdout, stderr = ssh.exec_command(
            'tar -zxf {remote_path} -C /tmp'.format(remote_path=remote_path))
        stdout.channel.recv_exit_status()  # 阻塞直到 exec_command 命令执行完毕

        _, stdout, _ = ssh.exec_command(
            'mv /tmp/{hadoop_home} {hadoop_installation}'.format(hadoop_home=hadoop_home, hadoop_installation=hadoop_installation))
        stdout.channel.recv_exit_status()

        _, stdout, _ = ssh.exec_command(
            'chown -R hadoop {hadoop_home}'.format(hadoop_home=hadoop_home))
        stdout.channel.recv_exit_status()

        # 删除文件
        _, stdout, _ = ssh.exec_command(
            'rm -fr /tmp/{hadoop_top_dir}'.format(hadoop_top_dir=hadoop_top_dir))
        stdout.channel.recv_exit_status()
        sftp.remove(remote_path)

        # 退出ssh连接
        ssh.close()

# 删除原有的hadoop包
os.system('rm -f {local_path}'.format(local_path=local_path))

# 参考：
# 1、Python paramik：https://blog.csdn.net/u012881331/article/details/82881053
