from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
import pytz

class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False) 
    customer_name = Column(String, index=True, nullable=False)
    environment = Column(String, nullable=False)
    type = Column(String, nullable=True)

    cloud_platform = Column(String, default="aws")
    account_id = Column(String, index=True, nullable=False)
    region = Column(String, nullable=False)

    created_at_git = Column(String, nullable=True)
    updated_at_helm = Column(String, nullable=True)
    web_url = Column(String, nullable=True)

    infrastructure = relationship("Infrastructure", back_populates="environment", uselist=False, cascade="all, delete-orphan")
    cluster = relationship("Cluster", back_populates="environment", uselist=False, cascade="all, delete-orphan")
    data_store = relationship("DataStore", back_populates="environment", uselist=False, cascade="all, delete-orphan")
    application = relationship("Application", back_populates="environment", uselist=False, cascade="all, delete-orphan")
    aws_resources = relationship("AWSResource", back_populates="environment", uselist=False, cascade="all, delete-orphan")

class Infrastructure(Base):
    __tablename__ = "infrastructure"

    id = Column(Integer, primary_key=True, index=True)
    env_id = Column(Integer, ForeignKey("environments.id"), unique=True, nullable=False)
    
    vpc_id = Column(String, nullable=True)
    vpc_cidr = Column(String, nullable=True)
    subnet_app_1 = Column(String, nullable=True)
    subnet_app_2 = Column(String, nullable=True)
    subnet_app_3 = Column(String, nullable=True)
    instance_type = Column(String, nullable=True)
    is_multi_az = Column(Boolean, default=False)
    resource_group = Column(String, nullable=True)

    environment = relationship("Environment", back_populates="infrastructure")

class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True)
    env_id = Column(Integer, ForeignKey("environments.id"), unique=True, nullable=False)

    cluster_name = Column(String, nullable=False)
    helm_branch = Column(String, nullable=True)
    dashboard_url = Column(String, nullable=True)
    ingress_host = Column(String, nullable=True)
    has_ingress = Column(Boolean, default=False)
    has_autoscaler = Column(Boolean, default=False)

    environment = relationship("Environment", back_populates="cluster")

class DataStore(Base):
    __tablename__ = "data_stores"

    id = Column(Integer, primary_key=True, index=True)
    env_id = Column(Integer, ForeignKey("environments.id"), unique=True, nullable=False)

    rds_endpoint = Column(String, nullable=True)
    rds_class = Column(String, nullable=True)
    
    es_endpoint = Column(String, nullable=True)
    es_instance = Column(String, nullable=True)
    
    redis_host = Column(String, nullable=True)
    redis_cluster_id = Column(String, nullable=True)

    environment = relationship("Environment", back_populates="data_store")

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    env_id = Column(Integer, ForeignKey("environments.id"), unique=True, nullable=False)

    ecm_replicas = Column(Integer, nullable=True)
    ecm_cpu_limit = Column(String, nullable=True)
    ecm_mem_limit = Column(String, nullable=True)
    ecm_java_ops = Column(Text, nullable=True) 
    
    userms_replicas = Column(Integer, nullable=True)
    pam_enabled = Column(Boolean, default=False)
    ispm_enabled = Column(Boolean, default=False)
    apm_enabled = Column(Boolean, default=False)
    apm_url = Column(String, nullable=True)
    log_bucket = Column(String, nullable=True)

    environment = relationship("Environment", back_populates="application")

class AzureSubscription(Base):
    __tablename__ = "azure_subscriptions"

    id = Column(String, primary_key=True)
    subscription_name = Column(String, nullable=False)
    is_internal = Column(Boolean, default=False)

class AWSResource(Base):
    __tablename__ = "aws_resources"

    id = Column(Integer, primary_key=True, index=True)
    env_id = Column(Integer, ForeignKey("environments.id"), unique=True, nullable=False)
    last_synced = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')), onupdate=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))

    environment = relationship("Environment", back_populates="aws_resources")
    eks = relationship("EKSCluster", back_populates="aws_resource", uselist=False, cascade="all, delete-orphan")
    rds = relationship("RDSInstance", back_populates="aws_resource", uselist=False, cascade="all, delete-orphan")
    elasticsearch = relationship("ElasticSearch", back_populates="aws_resource", uselist=False, cascade="all, delete-orphan")

class EKSCluster(Base):
    __tablename__ = "eks_clusters"

    id = Column(Integer, primary_key=True, index=True)
    aws_resource_id = Column(Integer, ForeignKey("aws_resources.id"), unique=True, nullable=False)

    name = Column(String, nullable=False)
    status = Column(String, nullable=True)
    kubernetes_version = Column(String, nullable=True)
    endpoint = Column(String, nullable=True)
    arn = Column(String, nullable=True)
    vpc_id = Column(String, nullable=True)
    subnet_ids = Column(JSON, nullable=True)
    nat_gateway_ips = Column(JSON, nullable=True)
    total_nodes = Column(Integer, nullable=True)

    aws_resource = relationship("AWSResource", back_populates="eks")
    node_groups = relationship("EKSNodeGroup", back_populates="eks_cluster", cascade="all, delete-orphan")

class EKSNodeGroup(Base):
    __tablename__ = "eks_node_groups"

    id = Column(Integer, primary_key=True, index=True)
    eks_cluster_id = Column(Integer, ForeignKey("eks_clusters.id"), nullable=False)

    name = Column(String, nullable=False)
    instance_types = Column(JSON, nullable=True)
    desired_size = Column(Integer, nullable=True)
    min_size = Column(Integer, nullable=True)
    max_size = Column(Integer, nullable=True)
    status = Column(String, nullable=True)

    eks_cluster = relationship("EKSCluster", back_populates="node_groups")

class RDSInstance(Base):
    __tablename__ = "rds_instances"

    id = Column(Integer, primary_key=True, index=True)
    aws_resource_id = Column(Integer, ForeignKey("aws_resources.id"), unique=True, nullable=False)

    identifier = Column(String, nullable=False)
    endpoint = Column(String, nullable=True)
    status = Column(String, nullable=True)
    engine = Column(String, nullable=True)
    engine_version = Column(String, nullable=True)
    instance_class = Column(String, nullable=True)
    allocated_storage_gb = Column(Integer, nullable=True)
    multi_az = Column(Boolean, default=False)
    storage_encrypted = Column(Boolean, default=False)
    cpu_percent = Column(Float, nullable=True)
    free_storage_gb = Column(Float, nullable=True)
    connections = Column(Integer, nullable=True)

    aws_resource = relationship("AWSResource", back_populates="rds")

class ElasticSearch(Base):
    __tablename__ = "elasticsearch_domains"

    id = Column(Integer, primary_key=True, index=True)
    aws_resource_id = Column(Integer, ForeignKey("aws_resources.id"), unique=True, nullable=False)

    domain_name = Column(String, nullable=False)
    status = Column(String, nullable=True)
    version = Column(String, nullable=True)
    endpoint = Column(String, nullable=True)
    instance_type = Column(String, nullable=True)
    instance_count = Column(Integer, nullable=True)
    volume_size_gb = Column(Integer, nullable=True)

    aws_resource = relationship("AWSResource", back_populates="elasticsearch")