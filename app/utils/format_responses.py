def _format_fetch_aws_resources_response(cluster_name: str, account_id: str, region: str, aws_resource: models.AWSResource) -> dict:
    """Format database records into API response"""
    resources = {
        "cluster_name": cluster_name,
        "region": region,
        "timestamp": aws_resource.last_synced.isoformat(),
        "eks": None,
        "rds": None,
        "elasticsearch": None
    }
    
    if aws_resource.eks:
        eks = aws_resource.eks
        resources["eks"] = {
            "name": eks.name,
            "status": eks.status,
            "kubernetes_version": eks.kubernetes_version,
            "endpoint": eks.endpoint,
            "arn": eks.arn,
            "vpc_id": eks.vpc_id,
            "subnet_ids": eks.subnet_ids,
            "nat_gateway_ips": eks.nat_gateway_ips,
            "total_nodes": eks.total_nodes,
            "node_groups": [
                {
                    "name": ng.name,
                    "instance_types": ng.instance_types,
                    "desired_size": ng.desired_size,
                    "min_size": ng.min_size,
                    "max_size": ng.max_size,
                    "status": ng.status
                }
                for ng in eks.node_groups
            ]
        }
    
    if aws_resource.rds:
        rds = aws_resource.rds
        resources["rds"] = {
            "identifier": rds.identifier,
            "endpoint": rds.endpoint,
            "status": rds.status,
            "engine": rds.engine,
            "engine_version": rds.engine_version,
            "instance_class": rds.instance_class,
            "allocated_storage_gb": rds.allocated_storage_gb,
            "multi_az": rds.multi_az,
            "storage_encrypted": rds.storage_encrypted,
            "performance": {
                "cpu_percent": rds.cpu_percent,
                "free_storage_gb": rds.free_storage_gb,
                "connections": rds.connections
            }
        }
    
    if aws_resource.elasticsearch:
        es = aws_resource.elasticsearch
        resources["elasticsearch"] = {
            "domain_name": es.domain_name,
            "status": es.status,
            "version": es.version,
            "endpoint": es.endpoint,
            "instance_type": es.instance_type,
            "instance_count": es.instance_count,
            "volume_size_gb": es.volume_size_gb
        }
    
    return {
        "success": True,
        "cluster_name": cluster_name,
        "account_id": account_id,
        "region": region,
        "resources": resources
    }
