#!/bin/bash -e
set -x 
# To use this script without jetpack, re-implement
# 1) local_lsf_conf  - print the path of the local lsf.conf file
# 2) attribute_names - prints a list of attribute names
# 3) attribute_value - prints the value of an attribute given the name as the first argument
# There is also the is_blacklisted function you can edit to ignore certain attributes, like ncpus or mem.


function do_modification() {

	expr=LSF_LOCAL_RESOURCES=\"

	for attribute in $( attribute_names ); do
	    if [ $(is_blacklisted $attribute) != 0 ]; then
	        continue
	    fi;
		
	    value=$( attribute_value $attribute )
	    shopt -s nocasematch
		
		echo $attribute $value >&2

	    if [[ "$value" == "true" ]]; then
	        expr="$expr [resource $attribute]"
	    elif [[ "$value" == "false" ]]; then
	    	# not declaring a boolean resource is declaring it as false.
	    	true;
	    else
	        expr="$expr [resourcemap $value*$attribute]"
	    fi
	   
	   shopt -u nocasematch
	    
	done
	
	expr="$expr\""
	
	if grep -q "^LSF_LOCAL_RESOURCES=" $(local_lsf_conf) ; then
		echo sed -i s/^LSF_LOCAL_RESOURCES=.*/"$expr"/g $(local_lsf_conf) >&2
		cat $(local_lsf_conf) | sed 's/^LSF_LOCAL_RESOURCES=.*/'"$expr"/g > lsf.conf.tmp
		mv lsf.conf.tmp $(local_lsf_conf) 
	else
		cat $(local_lsf_conf) > lsf.conf.tmp
		printf "%s" "$expr" >> lsf.conf.tmp
		mv lsf.conf.tmp $(local_lsf_conf)
	fi
}


function local_lsf_conf() {
	echo $(jetpack config lsf.local_etc /etc/lsf)/lsf.conf
}


function should_skip_script() {
	# if jetpack is installed and the user has decided to skip
	set +e
	which jetpack 1>&2 2>/dev/null
	jetpack_exists=$?
	set -e

	if [ $jetpack_exists == 0 ]; then
		template=$(jetpack config cyclecloud.node.template execute)
		if [ "$template" == "master" ]; then
			echo 0
			return
		fi
		skip_modify_local_resources=$(jetpack config lsf.skip_modify_local_resources 0)
		if [ $skip_modify_local_resources != 0 ]; then
			echo skipping $0 because lsf.skip_modify_local_resources is set to $skip_modify_local_resources >&2
			echo 1
		else
		    echo 0
		fi
	else
		echo no jetpack installed, continuing >&2
		echo 0
	fi
}


function is_blacklisted() {
	# attributes we want exposed to allocate VMs but that we don't want to
	# override as a local resource
	blacklisted_attributes=("mem" "ncpus" "type" "ncores", "machinetypefull", "custom_script_uri")
	
    # ex: is_blacklisted "mem"
    if [[ "${blacklisted_attributes[@]}" =~ "$1" ]]; then
        echo 1
    else
    	echo 0
    fi
}


function attribute_names() {
    # To do this without jetpack, just replace this with
    # echo key1 key2 key3
    jetpack config lsf.attribute_names
}


function attribute_value() {
    # ex: attribute_value custom_attribute
    # To do this without jetpack, just replace this with
    # your own mechanism for looking up this key / values.
    # e.g. it could just be `echo $1` if they are environment variables
    jetpack config lsf.attributes.$1
}


if [ $( should_skip_script ) == 0 ]; then
	do_modification
fi
