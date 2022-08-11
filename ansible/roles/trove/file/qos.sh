#!/bin/bash

iops_and_instance_spec=(
'1000,1c2g'
'2000,2c4g'
'4000,2c8g'
'5000,4c8g'
'7000,4c16g'
'8000,8c16g'
'12000,8c32g')

#根据/etc/cinder/cinder.conf里的volume_backend_name配置设置
#ceph-ssd
volume_backend_name='ceph-rbd' 


if [ ! $volume_backend_name ]; then
	echo "volume_backend_name is null, please set and retry"
	exit 1
else
  	echo "volume_backend_name: ${volume_backend_name}"
fi

source /root/openrc

qos_list=`cinder qos-list`
type_list=`cinder type-list`
# echo $qos_list
# echo $type_list

for i in "${iops_and_instance_spec[@]}" ; do
	arr=(${i//,/ }) 
	iops=${arr[0]}
	instance_spec=${arr[1]}
 	echo $iops $instance_spec
 	
 	qos_name="spec-iops-${iops}"
 	type_name="type-iops-${iops}"

 	if [[ $qos_list =~ $qos_name ]] 
 	then
    	echo "qos: ${qos_name} is exists"
	else
    	qos_specs_id=`cinder qos-create ${qos_name} consumer=front-end total_iops_sec=${iops} | awk 'NR==5' | awk 'BEGIN{ FS="|" ; RS="|" } NF>0 { print $NF }' | awk 'NR==2'`
    	echo "qos: ${qos_name} is not exists, create qos_specs_id: ${qos_specs_id}" 
	fi
	
	if [[ $type_list =~ $type_name ]] 
 	then
    	echo "type: ${type_name} is exists"
	else
		volume_type_id=`cinder type-create ${type_name} --description=${instance_spec} | awk 'NR==4' | awk 'BEGIN{ FS="|" ; RS="|" } NF>0 { print $0 }'| awk 'NR==1'`
 		echo "type: ${type_name} is not exists, create volume_type_id: ${volume_type_id}"
 		type_key=`cinder type-key type-iops-${iops} set volume_backend_name=${volume_backend_name}`
 		echo "set type_key for ${type_name}"
	fi
	
	if [ $qos_specs_id ] && [ $volume_type_id ]; then
  		qos_associate=`cinder qos-associate ${qos_specs_id} ${volume_type_id}`
		echo "qos associate, type_name: ${type_name}, qos_name: ${qos_name}"
	else
  		echo "qos_specs_id or volume_type_id is null"
	fi
done
