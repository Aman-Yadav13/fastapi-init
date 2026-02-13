import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from app import models
from app.dependencies import get_current_user, get_db
from app.utils.format_responses import _format_fetch_aws_resources_response
from app.services.cloud_services import AWSResourceService

router = APIRouter(prefix="/api", tags=["AWS Resources"])

@router.get("/fetchCloudResources")
async def fetch_cloud_resources(
    cluster_name: str = Query(..., description="EKS cluster name"),
    account_id: str = Query(..., description="AWS account ID"),
    region: str = Query(..., description="AWS region"),
    force_refresh: bool = Query(False, description="Force refresh from AWS"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch AWS resources for a given cluster (requires authentication)"""
    
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_token = os.getenv("AWS_SESSION_TOKEN")
    
    if not all([aws_key, aws_secret, aws_token]):
        raise HTTPException(status_code=500, detail="AWS credentials not configured")
    
    env_record = db.query(models.Environment).join(
        models.Cluster
    ).filter(
        models.Cluster.cluster_name == cluster_name
    ).first()
    
    if not env_record:
        raise HTTPException(status_code=404, detail="Cluster not found in database")
    
    if env_record.aws_resources and not force_refresh:
        return _format_fetch_aws_resources_response(cluster_name, account_id, region, env_record.aws_resources)
    
    if force_refresh and env_record.aws_resources:
        db.delete(env_record.aws_resources)
        db.commit()
    
    rds_endpoint = env_record.data_store.rds_endpoint if env_record.data_store else None
    es_endpoint = env_record.data_store.es_endpoint if env_record.data_store else None
    
    aws_service = AWSResourceService(aws_key, aws_secret, aws_token, region)
    
    try:
        resources = aws_service.get_cluster_resources(
            cluster_name=cluster_name,
            rds_endpoint=rds_endpoint,
            es_endpoint=es_endpoint,
            redis_host=None
        )
        
        aws_resource = models.AWSResource(env_id=env_record.id)
        db.add(aws_resource)
        db.flush()
        
        if resources.get("eks") and not resources["eks"].get("error"):
            eks_data = resources["eks"]
            eks = models.EKSCluster(
                aws_resource_id=aws_resource.id,
                name=eks_data["name"],
                status=eks_data.get("status"),
                kubernetes_version=eks_data.get("kubernetes_version"),
                endpoint=eks_data.get("endpoint"),
                arn=eks_data.get("arn"),
                vpc_id=eks_data.get("vpc_id"),
                subnet_ids=eks_data.get("subnet_ids"),
                nat_gateway_ips=eks_data.get("nat_gateway_ips"),
                total_nodes=eks_data.get("total_nodes")
            )
            db.add(eks)
            db.flush()
            
            for ng in eks_data.get("node_groups", []):
                node_group = models.EKSNodeGroup(
                    eks_cluster_id=eks.id,
                    name=ng["name"],
                    instance_types=ng.get("instance_types"),
                    desired_size=ng.get("desired_size"),
                    min_size=ng.get("min_size"),
                    max_size=ng.get("max_size"),
                    status=ng.get("status")
                )
                db.add(node_group)
        
        if resources.get("rds") and not resources["rds"].get("error"):
            rds_data = resources["rds"]
            perf = rds_data.get("performance", {})
            rds = models.RDSInstance(
                aws_resource_id=aws_resource.id,
                identifier=rds_data["identifier"],
                endpoint=rds_data.get("endpoint"),
                status=rds_data.get("status"),
                engine=rds_data.get("engine"),
                engine_version=rds_data.get("engine_version"),
                instance_class=rds_data.get("instance_class"),
                allocated_storage_gb=rds_data.get("allocated_storage_gb"),
                multi_az=rds_data.get("multi_az", False),
                storage_encrypted=rds_data.get("storage_encrypted", False),
                cpu_percent=perf.get("cpu_percent"),
                free_storage_gb=perf.get("free_storage_gb"),
                connections=perf.get("connections")
            )
            db.add(rds)
        
        if resources.get("elasticsearch") and not resources["elasticsearch"].get("error"):
            es_data = resources["elasticsearch"]
            es = models.ElasticSearch(
                aws_resource_id=aws_resource.id,
                domain_name=es_data["domain_name"],
                status=es_data.get("status"),
                version=es_data.get("version"),
                endpoint=es_data.get("endpoint"),
                instance_type=es_data.get("instance_type"),
                instance_count=es_data.get("instance_count"),
                volume_size_gb=es_data.get("volume_size_gb")
            )
            db.add(es)
        
        db.commit()
        db.refresh(aws_resource)
        
        return _format_fetch_aws_resources_response(cluster_name, account_id, region, aws_resource)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


