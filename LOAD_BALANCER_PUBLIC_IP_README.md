# Load Balancer and Public IP Support

This implementation adds comprehensive support for AWS Load Balancers and Public IPs to the Cloud Inventory system.

## Features Added

### Load Balancers
- **Application Load Balancers (ALB)** - Layer 7 HTTP/HTTPS load balancers
- **Network Load Balancers (NLB)** - Layer 4 TCP/UDP load balancers  
- **Gateway Load Balancers (GWLB)** - Layer 3 gateway load balancers
- **Classic Load Balancers (CLB)** - Legacy Elastic Load Balancers

#### Load Balancer Data Captured:
- Basic info: Name, ARN, DNS name, type, scheme, state
- Network: VPC ID, availability zones, security groups
- Configuration: IP address type, hosted zone ID, creation time
- Target Groups: Health checks, protocols, ports, target types
- Listeners: Protocols, ports, SSL policies, certificates
- Attributes: Access logs, connection draining, cross-zone load balancing

### Public IPs
- **Elastic IPs (EIPs)** - Static public IPv4 addresses
- **NAT Gateway IPs** - Public IPs assigned to NAT Gateways
- **Load Balancer IPs** - Public IPs resolved from internet-facing load balancers
- **EC2 Instance IPs** - Auto-assigned public IPs on EC2 instances

#### Public IP Data Captured:
- IP addresses: Public IP, private IP mapping
- AWS metadata: Allocation ID, association ID, domain
- Resource association: Instance ID, network interface ID
- Source tracking: Resource type, ID, and name that owns the IP
- Tags and additional metadata

## Database Schema

### New Tables:
1. **load_balancers** - Main load balancer information
2. **target_groups** - Load balancer target group details
3. **load_balancer_listeners** - Listener configurations
4. **public_ips** - All public IP addresses and their sources

### Relationships:
- `AWSResource` → `LoadBalancer[]` (one-to-many)
- `AWSResource` → `PublicIP[]` (one-to-many)
- `LoadBalancer` → `TargetGroup[]` (one-to-many)
- `LoadBalancer` → `LoadBalancerListener[]` (one-to-many)

## API Response Format

```json
{
  "success": true,
  "cluster_name": "example-cluster",
  "account_id": "123456789012",
  "region": "us-east-1",
  "resources": {
    "load_balancers": [
      {
        "name": "example-alb",
        "arn": "arn:aws:elasticloadbalancing:...",
        "dns_name": "example-alb-123456789.us-east-1.elb.amazonaws.com",
        "type": "application",
        "scheme": "internet-facing",
        "state": "active",
        "vpc_id": "vpc-12345678",
        "target_groups": [...],
        "listeners": [...]
      }
    ],
    "public_ips": [
      {
        "public_ip": "203.0.113.1",
        "allocation_id": "eipalloc-12345678",
        "source_type": "eip",
        "source_name": "Production EIP",
        "instance_id": "i-1234567890abcdef0"
      }
    ]
  }
}
```

## Error Handling

The implementation includes comprehensive error handling:

- **Individual resource failures** don't stop the entire scan
- **Detailed logging** for troubleshooting AWS API issues
- **Graceful degradation** when permissions are insufficient
- **Retry logic** for transient AWS API errors

## AWS Permissions Required

### Load Balancers:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups", 
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:DescribeLoadBalancerAttributes",
        "elb:DescribeLoadBalancers",
        "elb:DescribeLoadBalancerAttributes"
      ],
      "Resource": "*"
    }
  ]
}
```

### Public IPs:
```json
{
  "Version": "2012-10-17", 
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeAddresses",
        "ec2:DescribeNatGateways",
        "ec2:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

## Installation Steps

1. **Run database migration:**
   ```bash
   cd backend
   python migrate_db.py
   ```

2. **Test the implementation:**
   ```bash
   python test_lb_ip.py
   ```

3. **Restart the backend service:**
   ```bash
   uvicorn app.main:app --reload
   ```

## Logging

The implementation provides detailed logging at multiple levels:

- **INFO**: Successful operations and resource counts
- **WARNING**: Non-critical failures (e.g., missing permissions for specific resources)
- **ERROR**: Critical failures that prevent resource scanning

Example log output:
```
INFO: Found 3 load balancers
INFO: Found 12 public IPs  
WARNING: Failed to get LB attributes for example-alb: AccessDenied
ERROR: Error fetching Classic load balancers: InvalidUserID.NotFound
```

## Performance Considerations

- **Parallel processing** for different resource types
- **Efficient AWS API usage** with proper pagination
- **Database bulk operations** for large datasets
- **Connection pooling** for database operations

## Future Enhancements

1. **Health status monitoring** for load balancer targets
2. **Cost analysis** for public IP usage
3. **Security group analysis** for load balancers
4. **SSL certificate expiration tracking**
5. **Traffic metrics integration** with CloudWatch

## Troubleshooting

### Common Issues:

1. **Missing permissions**: Check AWS IAM policies
2. **Region mismatch**: Ensure correct region configuration
3. **Rate limiting**: AWS API throttling during large scans
4. **DNS resolution failures**: Network connectivity for LB IP resolution

### Debug Mode:
Set logging level to DEBUG for detailed AWS API call information:
```python
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)
```