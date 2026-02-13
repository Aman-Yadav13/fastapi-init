import boto3
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class AWSResourceService:
    def __init__(self, aws_access_key: str, aws_secret_key: str, aws_session_token: str, region: str):
        self.session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_session_token=aws_session_token,
            region_name=region
        )
        self.region = region

    def get_cluster_resources(self, cluster_name: str, rds_endpoint: Optional[str] = None, 
                            es_endpoint: Optional[str] = None, redis_host: Optional[str] = None) -> Dict:
        resources = {
            "cluster_name": cluster_name,
            "region": self.region,
            "timestamp": datetime.utcnow().isoformat(),
            "eks": self._get_eks_cluster_info(cluster_name),
            "rds": self._get_rds_info(rds_endpoint) if rds_endpoint else None,
            "elasticsearch": self._get_elasticsearch_info(es_endpoint) if es_endpoint else None,
        }
        return resources

    def _get_eks_cluster_info(self, cluster_name: str) -> Optional[Dict]:
        try:
            eks = self.session.client('eks')
            response = eks.describe_cluster(name=cluster_name)
            cluster = response['cluster']

            node_groups = []
            total_nodes = 0
            try:
                ng_response = eks.list_nodegroups(clusterName=cluster_name)
                for ng_name in ng_response.get('nodegroups', []):
                    ng_detail = eks.describe_nodegroup(clusterName=cluster_name, nodegroupName=ng_name)
                    desired = ng_detail['nodegroup']['scalingConfig'].get('desiredSize', 0)
                    total_nodes += desired
                    node_groups.append({
                        "name": ng_name,
                        "instance_types": ng_detail['nodegroup'].get('instanceTypes', []),
                        "desired_size": desired,
                        "min_size": ng_detail['nodegroup']['scalingConfig'].get('minSize', 0),
                        "max_size": ng_detail['nodegroup']['scalingConfig'].get('maxSize', 0),
                        "status": ng_detail['nodegroup'].get('status')
                    })
            except Exception as e:
                logger.warning(f"Node groups error: {str(e)}")

            vpc_id = cluster.get('resourcesVpcConfig', {}).get('vpcId')
            nat_ips = self._get_nat_ips(vpc_id) if vpc_id else []

            return {
                "name": cluster_name,
                "status": cluster.get('status'),
                "kubernetes_version": cluster.get('version'),
                "endpoint": cluster.get('endpoint'),
                "arn": cluster.get('arn'),
                "vpc_id": vpc_id,
                "subnet_ids": cluster.get('resourcesVpcConfig', {}).get('subnetIds', []),
                "nat_gateway_ips": nat_ips,
                "node_groups": node_groups,
                "total_nodes": total_nodes
            }
        except Exception as e:
            logger.error(f"EKS error: {str(e)}")
            return {"error": str(e)}

    def _get_rds_info(self, endpoint: str) -> Optional[Dict]:
        try:
            db_id = endpoint.split('.')[0]
            rds = self.session.client('rds')
            response = rds.describe_db_instances(DBInstanceIdentifier=db_id)
            db = response['DBInstances'][0]

            cw = self.session.client('cloudwatch')
            cpu = self._get_metric(cw, 'AWS/RDS', 'CPUUtilization', [{'Name': 'DBInstanceIdentifier', 'Value': db_id}])
            free_storage = self._get_metric(cw, 'AWS/RDS', 'FreeStorageSpace', [{'Name': 'DBInstanceIdentifier', 'Value': db_id}])
            connections = self._get_metric(cw, 'AWS/RDS', 'DatabaseConnections', [{'Name': 'DBInstanceIdentifier', 'Value': db_id}])

            allocated = db.get('AllocatedStorage', 0)
            free_gb = (free_storage / (1024**3)) if free_storage else 0

            return {
                "identifier": db_id,
                "endpoint": db.get('Endpoint', {}).get('Address'),
                "status": db.get('DBInstanceStatus'),
                "engine": db.get('Engine'),
                "engine_version": db.get('EngineVersion'),
                "instance_class": db.get('DBInstanceClass'),
                "allocated_storage_gb": allocated,
                "multi_az": db.get('MultiAZ'),
                "storage_encrypted": db.get('StorageEncrypted'),
                "performance": {
                    "cpu_percent": round(cpu, 2) if cpu else None,
                    "free_storage_gb": round(free_gb, 2),
                    "connections": int(connections) if connections else 0
                }
            }
        except Exception as e:
            logger.error(f"RDS error: {str(e)}")
            return {"error": str(e)}

    def _get_elasticsearch_info(self, endpoint: str) -> Optional[Dict]:
        try:
            domain_parts = endpoint.split('.')[0]
            if domain_parts.startswith('vpc-'):
                domain_parts = domain_parts[4:]
            parts = domain_parts.rsplit('-', 1)
            domain_name = parts[0] if len(parts) > 1 else domain_parts
            
            es = self.session.client('es')
            response = es.describe_elasticsearch_domain(DomainName=domain_name)
            domain = response['DomainStatus']

            config = domain.get('ElasticsearchClusterConfig', {})
            ebs = domain.get('EBSOptions', {})
            
            # VPC domains use Endpoints.vpc, public domains use Endpoint
            endpoint = domain.get('Endpoint') or domain.get('Endpoints', {}).get('vpc')

            return {
                "domain_name": domain_name,
                "status": "processing" if domain.get('Processing') else "available",
                "version": domain.get('ElasticsearchVersion'),
                "endpoint": endpoint,
                "instance_type": config.get('InstanceType'),
                "instance_count": config.get('InstanceCount'),
                "volume_size_gb": ebs.get('VolumeSize', 0)
            }
        except Exception as e:
            logger.error(f"ES error: {str(e)}")
            return {"error": str(e)}


    def _get_nat_ips(self, vpc_id: str) -> List[str]:
        try:
            ec2 = self.session.client('ec2')
            response = ec2.describe_nat_gateways(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}, {'Name': 'state', 'Values': ['available']}]
            )
            ips = []
            for nat in response.get('NatGateways', []):
                for addr in nat.get('NatGatewayAddresses', []):
                    if addr.get('PublicIp'):
                        ips.append(addr['PublicIp'])
            return ips
        except:
            return []

    def _get_metric(self, cw, namespace: str, metric: str, dims: List[Dict]) -> Optional[float]:
        try:
            end = datetime.utcnow()
            start = end - timedelta(minutes=10)
            response = cw.get_metric_statistics(
                Namespace=namespace, MetricName=metric, Dimensions=dims,
                StartTime=start, EndTime=end, Period=300, Statistics=['Average']
            )
            datapoints = response.get('Datapoints', [])
            return sorted(datapoints, key=lambda x: x['Timestamp'])[-1]['Average'] if datapoints else None
        except:
            return None
