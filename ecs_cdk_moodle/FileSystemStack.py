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
    aws_ecs as _ecs,
    aws_rds as _rds,
    aws_efs as _efs,
    aws_ecr_assets as _ecr_assets,
    aws_elasticloadbalancingv2 as _elbv2,
    aws_logs as _logs,
    core as cdk
)

class MoodleFileSystemStackProperties:

    def __init__(
            self,
            vpc: _ec2.Vpc,
    ) -> None:

        self.vpc = vpc

class MoodleFileSystemStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,
                 properties: MoodleFileSystemStackProperties, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # define shared file system
        self.file_system = _efs.FileSystem(
            self, "MoodleFileSystem",
            vpc=properties.vpc,
            performance_mode=_efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=_efs.ThroughputMode.BURSTING
        )


