#!/bin/bash

if [ -f lsf.tar ]; then
  tar -C ../ -cvf lsf-blobs.tar blobs 
fi

mkdir -p logs
DATESTAMP=$(date +'%Y%m%d%M%S')
if [ "$(uname)" == "Darwin" ]; then
    IMAGE_HASH=$(openssl rand -base64 12 |md5 |head -c8;echo)        
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    IMAGE_HASH=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 8 ; echo '')
fi

echo $IMAGE_HASH
IMAGE_NAME=lsf-execute-${DATESTAMP}-${IMAGE_HASH}
packer build -var "client_id=$APPLICATION_ID" \
  -var "client_secret=$APPLICATION_SECRET" \
  -var "subscription_id=$SUBSCRIPTION_ID" \
  -var "tenant_id=$TENANT_ID" \
  -var "application_id=$APPLICATION_ID" \
  -var "resource_group=$RESOURCE_GROUP" \
  -var "location=$LOCATION" \
  -var "image_hash=$IMAGE_HASH" \
  -var "image_name=$IMAGE_NAME" \
  build.json | tee logs/${APP_NAME}-${DATESTAMP}-${IMAGE_HASH}.log


