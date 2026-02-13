import pandas as pd
import logging
import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app import models

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("population_job.log")
    ]
)
logger = logging.getLogger(__name__)


def parse_bool(value):
    """
    Robustly parses boolean values from various CSV formats.
    Handles: 'TRUE', 'FALSE', 'yes', 'no', 'true', 'false', boolean types, and None.
    """
    if pd.isna(value) or value == "":
        return False
    
    if isinstance(value, bool):
        return value
        
    v_str = str(value).strip().lower()
    return v_str in ['true', 'yes', '1', 't', 'on']

def clean_value(value):
    """Returns None if the value is NaN or empty, otherwise returns the value."""
    if pd.isna(value) or value == "" or str(value).lower() == "na":
        return None
    return str(value)

def populate_database(csv_path: str):
    logger.info(f"Starting database population from file: {csv_path}")
    
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return

    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Successfully loaded CSV. Total rows found: {len(df)}")
    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        return

    db: Session = SessionLocal()
    
    success_count = 0
    error_count = 0
    
    try:
        for index, row in df.iterrows():
            try:
                slug = clean_value(row.get('CUSTOMER_ENV'))
                if not slug:
                    logger.warning(f"Row {index + 1}: Skipped - Missing CUSTOMER_ENV (Slug)")
                    continue

                customer_name = clean_value(row.get('customer_name_appinstance'))
                environment_name = clean_value(row.get('environment_appinstance'))
                
                if not customer_name or not environment_name:
                    logger.warning(f"Row {index + 1}: Missing customer/env name for slug {slug}. Attempting derivation.")
                    parts = slug.split('-')
                    if len(parts) >= 2:
                        customer_name = parts[0]
                        environment_name = parts[-1]
                    else:
                        logger.error(f"Row {index + 1}: Could not derive customer/env for {slug}. Skipping.")
                        continue

                env_record = db.query(models.Environment).filter(models.Environment.slug == slug).first()
                
                if not env_record:
                    env_record = models.Environment(slug=slug)
                    db.add(env_record)
                    logger.info(f"Row {index + 1}: Creating new environment '{slug}'")
                
                env_record.customer_name = customer_name
                env_record.environment = environment_name
                env_record.type = clean_value(row.get('customer_tier_appinstance'))
                env_record.cloud_platform = clean_value(row.get('cloud_platform')) or "aws"
                env_record.account_id = clean_value(row.get('Account')) or "UNKNOWN"
                env_record.region = clean_value(row.get('Region')) or clean_value(row.get('aws_region_appinstance')) or "us-east-1"
                env_record.created_at_git = clean_value(row.get('CreatedAt'))
                env_record.updated_at_helm = clean_value(row.get('HelmFileTimeStamp'))
                if customer_name and environment_name:
                    env_record.web_url = f"https://gitlab.com/saviynt/cloud-ops/customer-instances/{customer_name}/{environment_name}/appinstance"
                else:
                    env_record.web_url = None
                db.commit()
                db.refresh(env_record)

            
                if env_record.infrastructure:
                    db.delete(env_record.infrastructure)
                
                infra_data = models.Infrastructure(
                    env_id=env_record.id,
                    vpc_id=clean_value(row.get('VPCID_infra-input')),
                    vpc_cidr=clean_value(row.get('VPCCIDR_infra-input')),
                    subnet_app_1=clean_value(row.get('AppSubnetCIDR1_infra-input')),
                    subnet_app_2=clean_value(row.get('AppSubnetCIDR2_infra-input')),
                    subnet_app_3=clean_value(row.get('AppSubnetCIDR3_infra-input')),
                    instance_type=clean_value(row.get('InstanceType_infra-input')),
                    is_multi_az=parse_bool(row.get('MultiAZ_infra-input')),
                    resource_group = (
                        clean_value(row.get('resource_group_appinstance')) or 
                        clean_value(row.get('AKSMCRGName_infra-output'))
                    )
                )
                db.add(infra_data)

                if env_record.cluster:
                    db.delete(env_record.cluster)
                
                raw_cluster_name = (
                    clean_value(row.get('cluster_name_cluster')) or 
                    clean_value(row.get('aks_cluster_name_cluster')) or 
                    clean_value(row.get('AKSClusterName_infra-output')) or 
                    clean_value(row.get('cluster_name_appinstance')) or
                    "Unknown"
                )

                if raw_cluster_name.upper() == "NA":
                    raw_cluster_name = "Unknown"

                cluster_data = models.Cluster(
                    env_id=env_record.id,
                    cluster_name=raw_cluster_name,
                    helm_branch=clean_value(row.get('helm_branch_cluster')) or clean_value(row.get('helm_branch_appinstance')),
                    
                    dashboard_url=(
                        clean_value(row.get('k8dashboard_hostname_cluster')) or 
                        clean_value(row.get('aks_dashboard_url_cluster')) # Example for Azure
                    ),
                    
                    ingress_host=clean_value(row.get('ingress-host_appinstance')),
                    has_ingress=parse_bool(row.get('ingress-nginx-enabled_cluster')),
                    has_autoscaler=parse_bool(row.get('cluster_autoscaler_enabled', False))
                )
                db.add(cluster_data)

                if env_record.data_store:
                    db.delete(env_record.data_store)

                data_store_data = models.DataStore(
                    env_id=env_record.id,
                    rds_endpoint=clean_value(row.get('RDSEndpoint_infra-output')),
                    rds_class=clean_value(row.get('RDSInstanceClass_infra-input')),
                    
                    es_endpoint=clean_value(row.get('Elasticsearch_endpoint_infra-output')),
                    es_instance=clean_value(row.get('ESInstanceType_infra-input')),
                    
                    redis_host=clean_value(row.get('redis_hostname_appinstance')),
                    redis_cluster_id=clean_value(row.get('RedisClusterID_infra-output'))
                )
                db.add(data_store_data)

                if env_record.application:
                    db.delete(env_record.application)

                app_data = models.Application(
                    env_id=env_record.id,
                    ecm_replicas=int(row.get('ecm-worker-replicas_appinstance')) if clean_value(row.get('ecm-worker-replicas_appinstance')) and str(row.get('ecm-worker-replicas_appinstance')).isdigit() else None,
                    ecm_cpu_limit=clean_value(row.get('ecm-worker-resources-limits-cpu_appinstance')),
                    ecm_mem_limit=clean_value(row.get('ecm-worker-resources-limits-memory_appinstance')),
                    ecm_java_ops=clean_value(row.get('ecm-worker-java_ops_appinstance')),
                    
                    userms_replicas=int(row.get('userms-replicas_appinstance')) if clean_value(row.get('userms-replicas_appinstance')) and str(row.get('userms-replicas_appinstance')).isdigit() else None,
                    ispm_enabled=parse_bool(row.get('ispm_services_enabled_appinstance')),
                    pam_enabled=parse_bool(row.get('pam_services_enabled_appinstance')),
                    apm_enabled=parse_bool(row.get('enabled_apm_monitoring_appinstance')),
                    apm_url=clean_value(row.get('apm_server_url_appinstance')),
                    log_bucket=clean_value(row.get('recording_bucket_appinstance'))
                )
                db.add(app_data)

                db.commit()
                success_count += 1
                
            except Exception as e:
                db.rollback()
                error_count += 1
                logger.error(f"Row {index + 1}: Failed to process. Error: {str(e)}")
                continue

    except Exception as e:
        logger.critical(f"Critical script failure: {e}")
    finally:
        db.close()
        logger.info(f"Population complete. Success: {success_count}, Errors: {error_count}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(current_dir, "../data/catapult_report.csv")
    
    populate_database(csv_file_path)