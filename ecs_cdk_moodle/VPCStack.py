# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
from aws_cdk import (
    aws_ec2 as _ec2,
    aws_elasticloadbalancingv2 as _elbv2,
    aws_certificatemanager as _cm,
    aws_route53 as _r53,    
    core as cdk
)

class MoodleVPCStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC in 2 AZs with separate Private and Public subnets and 2 NAT Gateways
        self.vpc = _ec2.Vpc(
            self, "MoodleVPC",
            max_azs=2,
            subnet_configuration=[
                _ec2.SubnetConfiguration(
                    subnet_type=_ec2.SubnetType.PUBLIC,
                    name="Public",
                    cidr_mask=24
                ),
                _ec2.SubnetConfiguration(
                    subnet_type=_ec2.SubnetType.PRIVATE,
                    name="Private",
                    cidr_mask=24,
                )
            ],
            nat_gateway_provider=_ec2.NatProvider.gateway(),
            nat_gateways=2,
        )
        
        cdk.CfnOutput(self, "MoodleVPCID",
                       value=self.vpc.vpc_id)


