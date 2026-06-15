# Deep-research worker — Phase 2 (AWS) setup

Phase 2 adds the Fargate infrastructure to `template.yaml` (ECR, ECS cluster +
task definition, a minimal public-subnet VPC with no NAT, IAM roles, a Secrets
Manager secret, a log group) and a CI step that builds + pushes the worker image.

**Two one-time actions are required before it deploys cleanly.** Until they're
done, the SAM-deploy step fails (CloudFormation rolls back — nothing existing is
touched). Both need the AWS **account owner** (admin).

---

## ⚠️ Why this is on a branch, not main
Merging to `main` triggers the CI `deploy` job, which runs `sam deploy`. With the
new resources, that deploy **needs the IAM permissions in step 1** — otherwise it
fails and (because the job stops on failure) the dashboard deploy is skipped too.
So: **do step 1 first, then merge this branch to `main`.**

---

## Step 1 — Expand the CI deploy role (`company-urban-deploy`)
The OIDC role is currently scoped to S3/IAM/Lambda/DynamoDB. CloudFormation now
also creates ECR/ECS/EC2(VPC)/SecretsManager/Logs resources, and CI pushes an
image to ECR. Attach this policy to the role (`arn:aws:iam::824980746386:role/company-urban-deploy`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "EcrManageAndPush", "Effect": "Allow", "Resource": "*", "Action": [
      "ecr:CreateRepository","ecr:DeleteRepository","ecr:DescribeRepositories",
      "ecr:PutLifecyclePolicy","ecr:GetLifecyclePolicy","ecr:TagResource","ecr:ListTagsForResource",
      "ecr:SetRepositoryPolicy","ecr:GetRepositoryPolicy",
      "ecr:GetAuthorizationToken","ecr:BatchCheckLayerAvailability","ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload","ecr:UploadLayerPart","ecr:CompleteLayerUpload","ecr:PutImage","ecr:BatchGetImage" ] },
    { "Sid": "EcsManage", "Effect": "Allow", "Resource": "*", "Action": [
      "ecs:CreateCluster","ecs:DeleteCluster","ecs:DescribeClusters","ecs:TagResource","ecs:UntagResource",
      "ecs:RegisterTaskDefinition","ecs:DeregisterTaskDefinition","ecs:DescribeTaskDefinition","ecs:ListTaskDefinitions" ] },
    { "Sid": "Ec2VpcManage", "Effect": "Allow", "Resource": "*", "Action": [
      "ec2:CreateVpc","ec2:DeleteVpc","ec2:ModifyVpcAttribute","ec2:DescribeVpcs","ec2:DescribeVpcAttribute",
      "ec2:CreateSubnet","ec2:DeleteSubnet","ec2:ModifySubnetAttribute","ec2:DescribeSubnets",
      "ec2:CreateInternetGateway","ec2:DeleteInternetGateway","ec2:AttachInternetGateway","ec2:DetachInternetGateway","ec2:DescribeInternetGateways",
      "ec2:CreateRouteTable","ec2:DeleteRouteTable","ec2:CreateRoute","ec2:DeleteRoute","ec2:AssociateRouteTable","ec2:DisassociateRouteTable","ec2:DescribeRouteTables",
      "ec2:CreateSecurityGroup","ec2:DeleteSecurityGroup","ec2:AuthorizeSecurityGroupEgress","ec2:RevokeSecurityGroupEgress","ec2:DescribeSecurityGroups","ec2:DescribeSecurityGroupRules",
      "ec2:CreateTags","ec2:DeleteTags","ec2:DescribeAvailabilityZones","ec2:DescribeNetworkInterfaces" ] },
    { "Sid": "SecretsManage", "Effect": "Allow",
      "Resource": "arn:aws:secretsmanager:us-east-1:824980746386:secret:company-urban-research-*", "Action": [
      "secretsmanager:CreateSecret","secretsmanager:DeleteSecret","secretsmanager:DescribeSecret",
      "secretsmanager:TagResource","secretsmanager:GetResourcePolicy" ] },
    { "Sid": "LogsManage", "Effect": "Allow", "Resource": "*", "Action": [
      "logs:CreateLogGroup","logs:DeleteLogGroup","logs:PutRetentionPolicy","logs:DescribeLogGroups",
      "logs:TagResource","logs:ListTagsForResource" ] },
    { "Sid": "PassResearchRolesToEcs", "Effect": "Allow", "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::824980746386:role/company-urban-stack-*",
      "Condition": { "StringEquals": { "iam:PassedToService": "ecs-tasks.amazonaws.com" } } }
  ]
}
```
(If the role's existing IAM permissions aren't already scoped to create `company-urban-stack-*` roles, also allow `iam:CreateRole`/`PutRolePolicy`/`AttachRolePolicy`/`DeleteRole`/`DeleteRolePolicy`/`DetachRolePolicy` on `arn:aws:iam::824980746386:role/company-urban-stack-*`.)

## Step 2 — Set the worker's ANTHROPIC_API_KEY (after the first successful deploy)
The stack creates the secret **empty**. Once the stack deploys, set its value once
(CFN never overwrites it again):

```bash
aws secretsmanager put-secret-value --region us-east-1 \
  --secret-id company-urban-research-anthropic-key-prod \
  --secret-string "sk-ant-..."   # the key the box already uses
```

---

## Deploy
1. Do **Step 1**.
2. Merge this branch to `main` → CI runs `sam deploy` (creates the resources + ECR repo) and pushes the worker image.
3. Do **Step 2** (the secret now exists).
4. Verify: `aws cloudformation describe-stacks --stack-name company-urban-stack --query "Stacks[0].Outputs"` — you'll see `ResearchClusterArn`, `ResearchTaskDefinitionArn`, `ResearchSubnetId`, `ResearchSecurityGroupId`, `ResearchEcrRepoUri`.

## Cost
Nothing runs until a task is launched (Phase 3). No NAT gateway, no always-on
compute → the stack additions are ~$0/idle. A deep-research run is ~$0.04–0.09
(2 vCPU / 8 GB Fargate, per-second).

## Phase 3 — wiring (built; needs box config to go live)
The wiring is implemented:
- **comms → Fargate:** `comms/backend/cmd_brain.py` launches `ecs:RunTask` on a deep
  request (topic + room id as env overrides, public subnet/SG, `assignPublicIp=ENABLED`)
  and acks immediately. Degrades gracefully (returns a note) if Fargate isn't configured.
- **report back:** the container POSTs the report to `POST /rooms/{id}/post` on the comms
  backend (new endpoint) → added as a דפנה message; the UI idle-poll shows it live.

To make it live on the box, after Phase 2 is deployed:

**a. Let the box call ecs:RunTask** — attach to the box's EC2 instance role (preferred, no static keys):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "RunResearchTask", "Effect": "Allow", "Action": "ecs:RunTask",
      "Resource": "arn:aws:ecs:us-east-1:824980746386:task-definition/company-urban-research-prod:*" },
    { "Sid": "PassResearchRoles", "Effect": "Allow", "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::824980746386:role/company-urban-stack-*",
      "Condition": { "StringEquals": { "iam:PassedToService": "ecs-tasks.amazonaws.com" } } }
  ]
}
```
(No instance role? Make an IAM user with this policy and put its `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` in the shared `.env` + the sync whitelist.)

**b. Set the box env** (add to the shared `.env`, then `bash deploy/sync-box-env.sh`) — IDs come from the Phase 2 stack outputs:
```
RESEARCH_ECS_CLUSTER=company-urban-research-prod
RESEARCH_TASK_DEF=company-urban-research-prod
RESEARCH_SUBNET=<ResearchSubnetId>
RESEARCH_SG=<ResearchSecurityGroupId>
AWS_REGION=us-east-1
RESEARCH_POST_TOKEN=<random string>   # optional; enforced on /post if set
```

**c. Install boto3** in the box's comms Python env, then restart comms (`deploy-box.sh`
restarts comms but doesn't pip-install comms deps).

Once a–c are done: `@דפנה תחקרי לעומק …` in a room → instant ack → a Fargate task runs
the research → the report lands back in the room. Until then, `cmd_brain` sees no
Fargate config and replies that there's no run target (no harm).
