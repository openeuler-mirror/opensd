opensd 说明
=====================

opensd用于批量地脚本化部署openstack各组件服务。

  *  本文档将第一台控制节点作为部署节点，可以根据实际情况选取其他节点作为部署节点

部署步骤
========

## 1. 部署前需要确认的信息

  - 两个VIP（虚拟IP）地址，一个控制节点用，一个cell节点用
  - 业务网vlan范围
  - 一台ceph_monitor主机ip地址
  - 装操作系统时，需将selinux设置为disable
  - 装操作系统时，将/etc/ssh/sshd_config配置文件内的UseDNS设置为no
  - 操作系统语言应设置为英文
  - 部署之前请确保所有计算节点/etc/hosts文件内没有对计算主机的解析，例如：如果有ecm00x的解析都需要将该条解析删除(目前已知的是在计算和ceph融合部署时会有这种情况)

## 2. ceph pool与认证创建

**在任意一台ceph monitor节点执行:**
### 2.1 创建pool:

```shell
ceph osd pool create volumes 2048
ceph osd pool create images 2048
```

### 2.2 初始化pool

```shell
rbd pool init volumes
rbd pool init images
```

### 2.3 创建用户认证

```shell
ceph auth get-or-create client.glance mon 'profile rbd' osd 'profile rbd pool=images' mgr 'profile rbd pool=images'
ceph auth get-or-create client.cinder mon 'profile rbd' osd 'profile rbd pool=volumes, profile rbd pool=images' mgr 'profile rbd pool=volumes'
```

## 3. 配置lvm

**根据物理机磁盘配置与闲置情况，为mysql数据目录挂载额外的磁盘空间。示例如下（根据实际情况做配置）：**


```
fdisk -l
Disk /dev/sdd: 479.6 GB, 479559942144 bytes, 936640512 sectors
Units = sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 4096 bytes
I/O size (minimum/optimal): 4096 bytes / 4096 bytes
Disk label type: dos
Disk identifier: 0x000ed242
创建分区
parted /dev/sdd
mkparted 0 -1
创建pv
partprobe /dev/sdd1
pvcreate /dev/sdd1
创建、激活vg
vgcreate vg_mariadb /dev/sdd1
vgchange -ay vg_mariadb
查看vg容量
vgdisplay
--- Volume group ---
VG Name vg_mariadb
System ID
Format lvm2
Metadata Areas 1
Metadata Sequence No 2
VG Access read/write
VG Status resizable
MAX LV 0
Cur LV 1
Open LV 1
Max PV 0
Cur PV 1
Act PV 1
VG Size 446.62 GiB
PE Size 4.00 MiB
Total PE 114335
Alloc PE / Size 114176 / 446.00 GiB
Free PE / Size 159 / 636.00 MiB
VG UUID bVUmDc-VkMu-Vi43-mg27-TEkG-oQfK-TvqdEc
创建lv
lvcreate -L 446G -n lv_mariadb vg_mariadb
格式化磁盘并获取卷的UUID
mkfs.ext4 /dev/mapper/vg_mariadb-lv_mariadb
blkid /dev/mapper/vg_mariadb-lv_mariadb
/dev/mapper/vg_mariadb-lv_mariadb: UUID="98d513eb-5f64-4aa5-810e-dc7143884fa2" TYPE="ext4"
注：98d513eb-5f64-4aa5-810e-dc7143884fa2为卷的UUID
挂载磁盘
mount /dev/mapper/vg_mariadb-lv_mariadb /var/lib/mysql
rm -rf  /var/lib/mysql/*
```


## 4. 配置yum repo

**在部署节点执行：**

### 4.1 备份yum源

```shell
mkdir /etc/yum.repos.d/bak/
mv /etc/yum.repos.d/*.repo /etc/yum.repos.d/bak/
```

### 4.2 配置yum repo

```shell
cat > /etc/yum.repos.d/opensd.repo << EOF
[base]
name=opensd Base
baseurl=http://xx.xx.xx.xx
gpgcheck=0
enabled=1

EOF
```

### 4.3 更新yum缓存

```shell
yum clean all
yum makecache
```

## 5. 安装opensd

**在部署节点执行：**

### 5.1 克隆opensd源码并安装

```shell
git clone https://gitee.com/openeuler/opensd
cd opensd
python3 setup.py install
```

## 6. 做ssh互信

**在部署节点执行：**

### 6.1 生成密钥对

执行如下命令并一路回车

```shell
ssh-keygen
```

### 6.2 生成主机IP地址文件
示例：

```shell
cd /usr/local/share/opensd/tools/
vim auto_ssh_host_ip
172.20.108.36
172.20.108.45
```

### 6.3 更改密码并执行脚本
*将免密脚本`/usr/local/bin/opensd-auto-ssh`内123123替换为真实密码*

```shell
# 替换脚本内123123字符串
vim /usr/local/bin/opensd-auto-ssh
```

```shell
## 安装expect后执行脚本
yum install expect -y
opensd-auto-ssh
```

### 6.4 部署节点与ceph monitor做互信

```shell
ssh-copy-id root@x.x.x.x
```

## 7. 配置opensd

**在部署节点执行：**

### 7.1 生成随机密码
安装 python3-pbr, python3-utils, python3-pyyaml, python3-oslo-utils并随机生成密码
```shell
yum install python3-pbr python3-utils python3-pyyaml python3-oslo-utils -y
# 执行命令生成密码
opensd-genpwd
# 检查密码是否生成
cat /usr/local/share/opensd/etc_examples/opensd/passwords.yml
```

### 7.2 配置inventory文件


```shell
vim /usr/local/share/opensd/ansible/inventory/multinode
# 三台控制节点主机信息
[control]
rgcc0001.cn-rockydev-1 ansible_host=173.20.5.35 availability_zone=az01.cell01.cn-rockydev-1
rgcc0002.cn-rockydev-1 ansible_host=173.20.5.36 availability_zone=az01.cell01.cn-rockydev-1
rgcc0003.cn-rockydev-1 ansible_host=173.20.5.37 availability_zone=az01.cell01.cn-rockydev-1

# 网络节点信息，与控制节点保持一致
[network]
rgcc0001.cn-rockydev-1 ansible_host=173.20.5.35 availability_zone=az01.cell01.cn-rockydev-1
rgcc0002.cn-rockydev-1 ansible_host=173.20.5.36 availability_zone=az01.cell01.cn-rockydev-1
rgcc0003.cn-rockydev-1 ansible_host=173.20.5.37 availability_zone=az01.cell01.cn-rockydev-1

# cinder-volume服务节点信息，分下面两种情况，根据情况，选择一种填写。
# 1) 如果一个cell下只部署一个AZ，将三台cell节点信息填写到这个主机组
[storage]
cell01-1.cn-rockydev-1 ansible_host=172.20.33.61 availability_zone=az01.cell01.cn-rockydev-1
cell01-2.cn-rockydev-1 ansible_host=172.20.33.78 availability_zone=az01.cell01.cn-rockydev-1
cell01-3.cn-rockydev-1 ansible_host=172.20.33.82 availability_zone=az01.cell01.cn-rockydev-1
# 2） 如果一个cell下部署多个AZ，将每个AZ的计算节点的前三台填写到这个主机组，主机顺序请按AZ顺序填写（该示例是三个AZ情况）
[storage]
ecm0001.a.cn-rockydev-1 ansible_host=173.20.5.27 availability_zone=az01.cell01.cn-rockydev-1
ecm0002.a.cn-rockydev-1 ansible_host=173.20.5.28 availability_zone=az01.cell01.cn-rockydev-1
ecm0003.a.cn-rockydev-1 ansible_host=173.20.5.29 availability_zone=az01.cell01.cn-rockydev-1
ecm0001.b.cn-rockydev-1 ansible_host=173.20.5.30 availability_zone=az02.cell01.cn-rockydev-1
ecm0002.b.cn-rockydev-1 ansible_host=173.20.5.31 availability_zone=az02.cell01.cn-rockydev-1
ecm0003.b.cn-rockydev-1 ansible_host=173.20.5.32 availability_zone=az02.cell01.cn-rockydev-1
ecm0001.c.cn-rockydev-1 ansible_host=173.20.5.39 availability_zone=az03.cell02.cn-rockydev-1
ecm0002.c.cn-rockydev-1 ansible_host=173.20.5.40 availability_zone=az03.cell02.cn-rockydev-1
ecm0003.c.cn-rockydev-1 ansible_host=173.20.5.41 availability_zone=az03.cell02.cn-rockydev-1

# Cell1 集群信息
[cell-control-cell1]
clcc0001.cn-rockydev-1 ansible_host=173.20.5.24 availability_zone=az01.cell01.cn-rockydev-1
clcc0002.cn-rockydev-1 ansible_host=173.20.5.25 availability_zone=az01.cell01.cn-rockydev-1
clcc0003.cn-rockydev-1 ansible_host=173.20.5.26 availability_zone=az01.cell01.cn-rockydev-1

[compute-cell1]
ecm0001.a.cn-rockydev-1 ansible_host=173.20.5.27 availability_zone=az01.cell01.cn-rockydev-1
ecm0002.a.cn-rockydev-1 ansible_host=173.20.5.28 availability_zone=az01.cell01.cn-rockydev-1
ecm0003.a.cn-rockydev-1 ansible_host=173.20.5.29 availability_zone=az01.cell01.cn-rockydev-1
ecm0001.b.cn-rockydev-1 ansible_host=173.20.5.30 availability_zone=az02.cell01.cn-rockydev-1
ecm0002.b.cn-rockydev-1 ansible_host=173.20.5.31 availability_zone=az02.cell01.cn-rockydev-1
ecm0003.b.cn-rockydev-1 ansible_host=173.20.5.32 availability_zone=az02.cell01.cn-rockydev-1


[cell1:children]
cell-control-cell1
compute-cell1

# Cell2集群信息
[cell-control-cell2]
clcc0004.cn-rockydev-1 ansible_host=173.20.5.36 availability_zone=az03.cell02.cn-rockydev-1
clcc0005.cn-rockydev-1 ansible_host=173.20.5.37 availability_zone=az03.cell02.cn-rockydev-1
clcc0006.cn-rockydev-1 ansible_host=173.20.5.38 availability_zone=az03.cell02.cn-rockydev-1

[compute-cell2]
ecm0001.c.cn-rockydev-1 ansible_host=173.20.5.39 availability_zone=az03.cell02.cn-rockydev-1
ecm0002.c.cn-rockydev-1 ansible_host=173.20.5.40 availability_zone=az03.cell02.cn-rockydev-1
ecm0003.c.cn-rockydev-1 ansible_host=173.20.5.41 availability_zone=az03.cell02.cn-rockydev-1

[cell2:children]
cell-control-cell2
compute-cell2

[baremetal]

[compute-cell1-ironic]


# 填写所有cell集群的control主机组
[nova-conductor:children]
cell-control-cell1
cell-control-cell2

# 填写所有cell集群的compute主机组
[nova-compute:children]
compute-added
compute-cell1
compute-cell2

# 下面的主机组信息不需变动，保留即可
[compute-added]

[chrony-server:children]
control

[pacemaker:children]
control
......
......
```

### 7.3 配置全局变量
**注: 文档中提到的有注释配置项需要更改，其他参数不需要更改**

```shell
vim /usr/local/share/opensd/etc_examples/opensd/globals.yml
########################
# Network & Base options
########################
network_interface: "eth0" #管理网络的网卡名称
neutron_external_interface: "eth1" #业务网络的网卡名称
cidr_netmask: 24 #管理网的掩码
opensd_vip_address: 173.20.5.33  #控制节点虚拟IP地址
cell1_vip_address: 173.20.5.34 #cell1集群的虚拟IP地址
cell2_vip_address: 173.20.5.35 #cell2集群的虚拟IP地址
external_fqdn: "" #用于vnc访问虚拟机的外网域名地址
external_ntp_servers: [] #外部ntp服务器地址
yumrepo_host: 172.20.3.243 #yum源的IP地址
yumrepo_port: 38888 #yum源端口号
enviroment: test  #yum源的类型
upgrade_all_packages: "yes" #是否升级所有安装版的版本(执行yum upgrade)，初始部署资源请设置为"yes"
enable_miner: "no" #是否开启部署miner服务

enable_chrony: "no"
enable_pri_mariadb: "no" 
enable_hosts_file_modify: "no" # 扩容计算节点和部署ironic服务的时候，是否将节点信息添加到`/etc/hosts`

########################
# Available zone options
########################
az_cephmon_compose:
  - availability_zone: az01.cell01.cn-rockydev-1 #availability zone的名称，该名称必须与multinode主机文件内的az01的"availability_zone"值保持一致
    ceph_mon_host: 172.20.90.2 #az01对应的一台ceph monitor主机地址，部署节点需要与该主机做ssh互信
    reserve_vcpu_based_on_numa: "yes" # 根据numa node, 平均每个node预留vcpu
  - availability_zone: az02.cell01.cn-rockydev-1 #availability zone的名称，该名称必须与multinode主机文件内的az02的"availability_zone"值保持一致
    ceph_mon_host: 172.31.2.30 #az02对应的一台ceph monitor主机地址，部署节点需要与该主机做ssh互信
    reserve_vcpu_based_on_numa: "no" # 从第一个vcpu开始，顺序预留vcpu
  - availability_zone: az03.cell02.cn-rockydev-1 #availability zone的名称，该名称必须与multinode主机文件内的az03的"availability_zone"值保持一致
    ceph_mon_host: 172.20.90.2 #az03对应的一台ceph monitor主机地址，部署节点需要与该主机做ssh互信
    reserve_vcpu_based_on_numa: "yes" # 根据numa node, 平均每个node预留vcpu

# `reserve_vcpu_based_on_numa`配置为`yes` or `no`,举例说明：
NUMA node0 CPU(s): 0-15,32-47
NUMA node1 CPU(s): 16-31,48-63
当reserve_vcpu_based_on_numa: "yes":
vcpu_pin_set = 2-15,34-47,18-31,50-63
当reserve_vcpu_based_on_numa: "no":
vcpu_pin_set = 8-64

#######################
# Nova options
#######################
nova_reserved_host_memory_mb: 2048 #计算节点给计算服务预留的内存大小
enable_cells: "yes" #cell节点是否单独节点部署
support_gpu: "True" #cell节点是否有GPU服务器，如果有则为True，否则为False

#######################
# Neutron options
#######################
monitor_ip:
    - 172.20.2.9   #配置监控节点
    - 172.20.2.10
enable_meter_full_eip: True   #配置是否允许EIP全量监控，默认为True
enable_meter_port_forwarding: True   #配置是否允许port forwarding监控，默认为True
enable_meter_ecs_ipv6: True   #配置是否允许ecs_ipv6监控，默认为True
enable_meter: True    #配置是否开启监控，默认为True
is_sdn_arch: False    #配置是否是sdn架构，默认为False

# 默认使能的网络类型是vlan,vlan和vxlan两种类型只能二选一.
enable_vxlan_network_type: True  # 默认使能的网络类型是vlan,如果使用vxlan网络，配置为True, 如果使用vlan网络，配置为False.
enable_neutron_fwaas: True       # 环境有使用防火墙, 设置为True, 使能防护墙功能.
# Neutron provider
neutron_provider_networks:
  network_types: "{{ 'vxlan' if enable_vxlan_network_type else 'vlan' }}"
  network_vlan_ranges: "default:xxx:xxx" #部署之前规划的业务网络vlan范围
  network_mappings: "default:br-provider"
  network_interface: "{{ neutron_external_interface }}"
  network_vxlan_ranges: "xxxxxx:xxxxxx" #部署之前规划的业务网络vxlan范围

# 如下这些配置是SND控制器的配置参数, `enable_sdn_controller`设置为True, 使能SND控制器功能.
# 其他参数请根据部署之前的规划和SDN部署信息确定.
enable_sdn_controller: True
sdn_controller_ip_address:  # SDN控制器ip地址
sdn_controller_username:    # SDN控制器的用户名
sdn_controller_password:    # SDN控制器的用户密码

#######################
# Dimsagent options
#######################
enable_dimsagent: "no" # 安装镜像服务agent, 需要改为yes
# Address and domain name for s2
s3_address_domain_pair:
  - host_ip:           
    host_name:         

#######################
# Trove options
#######################
enable_trove: "no" #安装trove 需要改为yes
#default network
trove_default_neutron_networks:  #trove 的管理网络id `openstack network list|grep -w trove-mgmt|awk '{print$2}'`
#s3 setup(如果没有s3,以下值填null)
s3_endpoint_host_ip:   #s3的ip
s3_endpoint_host_name: #s3的域名
s3_endpoint_url:       #s3的url ·一般为http：//s3域名
s3_access_key:         #s3的ak 
s3_secret_key:         #s3的sk

#######################
# Ironic options
#######################
enable_ironic: "no" #是否开机裸金属部署，默认不开启
ironic_neutron_provisioning_network_uuid:
ironic_neutron_cleaning_network_uuid: "{{ ironic_neutron_provisioning_network_uuid }}"
ironic_dnsmasq_interface:
ironic_dnsmasq_dhcp_range:
ironic_tftp_server_address: "{{ hostvars[inventory_hostname]['ansible_' + ironic_dnsmasq_interface]['ipv4']['address'] }}"
# 交换机设备相关信息
neutron_ml2_conf_genericswitch:
  genericswitch:xxxxxxx:
    device_type:
    ngs_mac_address:
    ip:
    username:
    password:
    ngs_port_default_vlan:

# Package state setting
haproxy_package_state: "present"
mariadb_package_state: "present"
rabbitmq_package_state: "present"
memcached_package_state: "present"
ceph_client_package_state: "present"
keystone_package_state: "present"
glance_package_state: "present"
cinder_package_state: "present"
nova_package_state: "present"
neutron_package_state: "present"
miner_package_state: "present"
```

### 7.4 检查所有节点ssh连接状态
```shell
yum install ansible -y
ansible all -i /usr/local/share/opensd/ansible/inventory/multinode -m ping

# 执行结果显示每台主机都是"SUCCESS"即说明连接状态没问题,示例：
ecm0001.b.cn-rockydev-1 | SUCCESS => {
  "ansible_facts": {
      "discovered_interpreter_python": "/usr/bin/python3"
  },
  "changed": false,
  "ping": "pong"
}
```

## 8. 执行部署

**在部署节点执行：**

### 8.1 执行bootstrap

```shell
# 执行部署
opensd -i /usr/local/share/opensd/ansible/inventory/multinode bootstrap --forks 50
```
### 8.2 重启服务器
**注：执行重启的原因是:bootstrap可能会升内核,更改selinux配置或者有GPU服务器,如果装机过程已经是新版内核,selinux disable或者没有GPU服务器,则不需要执行该步骤**
1. 定制的centos x86操作系统不升级内核版本;
2. NeoKylin-Server-7.0-Hygon x86操作系统不升级内核版本;
3. NeoKylin-Server-7.0-aarch64 arm操作系统升级内核版本;

```shell
# 手动重启对应节点,执行命令
init6
# 重启完成后，再次检查连通性
ansible all -i /usr/local/share/opensd/ansible/inventory/multinode -m ping
# 重启完后操作系统后，再次启动yum源
cd /opt/repo/
python -m SimpleHTTPServer 38888 > /dev/null 2>&1  &
```
### 8.3 执行部署前检查

```shell
opensd -i /usr/local/share/opensd/ansible/inventory/multinode prechecks --forks 50
```
### 8.4 执行部署

```shell
ln -s /usr/bin/python3 /usr/bin/python

opensd -i /usr/local/share/opensd/ansible/inventory/multinode deploy --forks 50
```
