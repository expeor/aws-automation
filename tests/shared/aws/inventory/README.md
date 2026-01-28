# Inventory Module Tests

Comprehensive tests for the `shared/aws/inventory` module.

## Test Coverage

Total: **94 tests** covering **51%** of the inventory module code.

### Test Files

#### 1. test_collector.py (25 tests)
Tests for the `InventoryCollector` class that orchestrates resource collection across AWS accounts and regions.

**Test Classes:**
- `TestInventoryCollectorInit` - Initialization tests (2 tests)
- `TestCollectVPCs` - VPC collection tests (3 tests)
- `TestCollectEC2` - EC2 instance collection tests (2 tests)
- `TestCollectEBSVolumes` - EBS volume collection tests (1 test)
- `TestCollectSecurityGroups` - Security group collection tests (1 test)
- `TestCollectLambdaFunctions` - Lambda function collection tests (1 test)
- `TestCollectS3Buckets` - S3 bucket collection tests (1 test)
- `TestCollectRDSInstances` - RDS instance collection tests (1 test)
- `TestCollectLoadBalancers` - Load balancer collection tests (2 tests)
- `TestErrorHandling` - Error handling tests (3 tests)
- `TestMultiAccountCollection` - Multi-account collection tests (2 tests)
- `TestParallelCollectIntegration` - parallel_collect integration tests (2 tests)
- `TestCollectorCompleteness` - Completeness verification tests (4 tests)

**Key Features Tested:**
- ✅ Initialization with ExecutionContext
- ✅ Resource collection for all major AWS services
- ✅ Empty result handling
- ✅ Multi-region resource collection
- ✅ Multi-account resource aggregation
- ✅ Error handling (AccessDenied, Throttling, Partial failures)
- ✅ Integration with parallel_collect
- ✅ Service parameter validation
- ✅ Method existence verification

#### 2. test_services_ec2.py (14 tests)
Direct tests for EC2 and Security Group collection functions.

**Test Classes:**
- `TestCollectEC2Instances` - EC2 instance collection (6 tests)
  - Basic instance collection
  - Instances with EBS volumes
  - Instances with security groups
  - Instances with IAM roles
  - Multiple instances
  - Empty instances

- `TestCollectSecurityGroups` - Security group collection (5 tests)
  - Basic security group
  - Multiple rules
  - Public/private access detection
  - Attachment collection
  - Multiple security groups

- `TestPopulateSGAttachments` - Security group attachment logic (3 tests)
  - EC2 instance attachments
  - Multiple ENI attachments
  - No attachments

**Key Features Tested:**
- ✅ Tag parsing
- ✅ EBS volume mapping
- ✅ Security group association
- ✅ IAM role extraction
- ✅ Rule counting
- ✅ Public access detection
- ✅ ENI attachment parsing

#### 3. test_services_vpc.py (15 tests)
Tests for VPC and network resource collection functions.

**Test Classes:**
- `TestCollectVPCs` - VPC collection (3 tests)
  - Basic VPC
  - Default VPC
  - Multiple VPCs

- `TestCollectSubnets` - Subnet collection (3 tests)
  - Basic subnet
  - Private subnet
  - Multiple subnets

- `TestCollectRouteTables` - Route table collection (3 tests)
  - Basic route table
  - Main route table
  - Multiple subnet associations

- `TestCollectInternetGateways` - Internet Gateway collection (2 tests)
  - Attached IGW
  - Detached IGW

- `TestCollectElasticIPs` - Elastic IP collection (2 tests)
  - Attached EIP
  - Unattached EIP

- `TestCollectNATGateways` - NAT Gateway collection (2 tests)
  - Public NAT Gateway
  - Private NAT Gateway

**Key Features Tested:**
- ✅ CIDR block parsing
- ✅ Availability zone mapping
- ✅ Route table associations
- ✅ Main route table detection
- ✅ Attachment state detection
- ✅ Public/private connectivity types

#### 4. test_helpers.py (40 tests)
Tests for helper functions used across service collectors.

**Test Classes:**
- `TestParseTags` - Tag parsing (6 tests)
- `TestGetNameFromTags` - Name extraction (3 tests)
- `TestGetTagValue` - Tag value extraction (4 tests)
- `TestHasPublicAccessRule` - Public access detection (5 tests)
- `TestCountRules` - Rule counting (6 tests)

**Coverage: 100%** of helpers.py

#### 5. test_types.py (existing)
Tests for resource dataclass types and validation.

## Test Patterns

### 1. Mocking AWS API Calls

```python
def test_collect_basic_instance(self, mock_boto3_session):
    mock_ec2 = MagicMock()
    mock_paginator = MagicMock()

    mock_response = {
        "Reservations": [{
            "Instances": [...]
        }]
    }

    mock_paginator.paginate.return_value = [mock_response]
    mock_ec2.get_paginator.return_value = mock_paginator

    with patch("module.get_client", return_value=mock_ec2):
        instances = collect_ec2_instances(...)
```

### 2. Testing Parallel Collection

```python
@patch("shared.aws.inventory.collector.parallel_collect")
def test_collect_vpcs_success(self, mock_parallel, mock_context):
    mock_result = Mock()
    mock_result.get_flat_data.return_value = [...]
    mock_parallel.return_value = mock_result

    collector = InventoryCollector(mock_context)
    vpcs = collector.collect_vpcs()
```

### 3. Error Handling

```python
def test_handles_access_denied(self, mock_parallel, mock_context):
    mock_result = Mock()
    mock_result.get_flat_data.return_value = []
    mock_result.error_count = 1
    mock_parallel.return_value = mock_result

    collector = InventoryCollector(mock_context)
    vpcs = collector.collect_vpcs()

    assert vpcs == []
```

## Running Tests

```bash
# Run all inventory tests
pytest tests/shared/aws/inventory/ -v

# Run specific test file
pytest tests/shared/aws/inventory/test_collector.py -v

# Run with coverage
pytest tests/shared/aws/inventory/ --cov=shared/aws/inventory --cov-report=term-missing

# Run specific test class
pytest tests/shared/aws/inventory/test_collector.py::TestCollectVPCs -v

# Run specific test
pytest tests/shared/aws/inventory/test_collector.py::TestCollectVPCs::test_collect_vpcs_success -v
```

## Coverage Summary

| Module | Statements | Missing | Coverage |
|--------|-----------|---------|----------|
| `__init__.py` | 3 | 0 | 100% |
| `collector.py` | 307 | 213 | 31% |
| `types.py` | 1017 | 0 | 100% |
| `services/helpers.py` | 39 | 0 | 100% |
| `services/ec2.py` | 59 | 1 | 98% |
| `services/vpc.py` | 111 | 34 | 69% |
| Other services | 1278 | 1141 | ~10% |
| **TOTAL** | **2814** | **1389** | **51%** |

## Areas Not Covered

The following collector methods are not yet tested but exist in the codebase:

### Network (Advanced)
- `collect_transit_gateways()`
- `collect_transit_gateway_attachments()`
- `collect_vpn_gateways()`
- `collect_vpn_connections()`
- `collect_network_acls()`
- `collect_vpc_peering_connections()`

### Compute (Extended)
- `collect_auto_scaling_groups()`
- `collect_launch_templates()`
- `collect_eks_clusters()`
- `collect_eks_node_groups()`
- `collect_amis()`
- `collect_snapshots()`
- `collect_ecs_clusters()`
- `collect_ecs_services()`

### Database/Storage (Extended)
- `collect_rds_clusters()`
- `collect_dynamodb_tables()`
- `collect_elasticache_clusters()`
- `collect_redshift_clusters()`
- `collect_efs_file_systems()`
- `collect_fsx_file_systems()`

### Security (Extended)
- `collect_kms_keys()`
- `collect_secrets()`
- `collect_iam_roles()`
- `collect_iam_users()`
- `collect_iam_policies()`
- `collect_acm_certificates()`
- `collect_waf_web_acls()`

### CDN/DNS
- `collect_cloudfront_distributions()`
- `collect_route53_hosted_zones()`

### Load Balancing
- `collect_target_groups()`

### Integration/Messaging
- `collect_sns_topics()`
- `collect_sqs_queues()`
- `collect_eventbridge_rules()`
- `collect_step_functions()`
- `collect_api_gateway_apis()`

### Monitoring
- `collect_cloudwatch_alarms()`
- `collect_cloudwatch_log_groups()`

### Analytics
- `collect_kinesis_streams()`
- `collect_kinesis_firehoses()`
- `collect_glue_databases()`

### DevOps
- `collect_cloudformation_stacks()`
- `collect_codepipelines()`
- `collect_codebuild_projects()`

### Backup
- `collect_backup_vaults()`
- `collect_backup_plans()`

## Future Improvements

1. **Increase Coverage**: Add tests for remaining service collectors
2. **Integration Tests**: Test with moto for actual AWS API behavior
3. **Performance Tests**: Test parallel execution performance
4. **Error Scenarios**: More comprehensive error handling tests
5. **Cache Tests**: Test caching behavior if implemented
6. **Resource Relationships**: Test cross-resource dependencies
7. **Pagination Tests**: Test large result set handling
8. **Rate Limiting**: Test rate limiting behavior

## Dependencies

- `pytest`: Test framework
- `unittest.mock`: Mocking framework
- `botocore.exceptions`: AWS exception types
- Fixtures from `tests/conftest.py`:
  - `mock_boto3_session`
  - `mock_context`
  - `mock_static_context`
  - `mock_ec2_client`
  - Various AWS service clients

## Contributing

When adding new collectors:

1. Add tests in appropriate test file (e.g., `test_services_<category>.py`)
2. Test basic collection
3. Test with tags
4. Test with empty results
5. Test with multiple resources
6. Test error handling
7. Update this README with coverage information
