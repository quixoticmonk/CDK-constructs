from aws_cdk import (core, aws_s3 as _s3, aws_iam as _iam, aws_cloudfront as
                     _cfront, aws_cloudfront_origins as _cfront_origins)

from aws_cdk.aws_cloudfront import (CfnCloudFrontOriginAccessIdentity,
                                    PriceClass, SecurityPolicyProtocol,
                                    GeoRestriction, AllowedMethods,
                                    ViewerProtocolPolicy)


class S3StaticSiteConstruct(core.Construct):
    def __init__(self, scope: core.Construct, construct_id: str,
                 ss_context: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Access logging bucket for the S3 and Cloudfront

        ss = dict(self.node.try_get_context(ss_context))

        allowed_methods = AllowedMethods.ALLOW_GET_HEAD if ss[
            "cfront_allowed_methods"] == "ALLOW_GET_HEAD" else AllowedMethods.ALLOW_GET_HEAD_OPTIONS if ss[
                "cfront_allowed_methods"] == "ALLOW_GET_HEAD_OPTIONS" else AllowedMethods.ALLOW_ALL

        viewer_policy = ViewerProtocolPolicy.REDIRECT_TO_HTTPS if ss[
            "cfront_viewer_policy"] == "REDIRECT_TO_HTTPS" else ViewerProtocolPolicy.HTTPS_ONLY if ss[
                "cfront_viewer_policy"] == "HTTPS_ONLY" else ViewerProtocolPolicy.ALLOW_ALL

        price_class = PriceClass.PRICE_CLASS_ALL if ss[
            "cfront_price_class"] == "PRICE_CLASS_ALL" else PriceClass.PRICE_CLASS_200 if ss[
                "cfront_price_class"] == "PRICE_CLASS_200" else PriceClass.PRICE_CLASS_100

        # Creating the access logs bucket

        access_log_bucket = _s3.Bucket(
            self,
            ss["access_logs_bucket_name"],
            bucket_name=ss["access_logs_bucket_name"],
            encryption=_s3.BucketEncryption.KMS_MANAGED,
            removal_policy=core.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # S3 bucket for the static site

        source_bucket = _s3.Bucket(
            self,
            ss["static_site_bucket_name"],
            bucket_name=ss["static_site_bucket_name"],
            encryption=_s3.BucketEncryption.KMS_MANAGED,
            removal_policy=core.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            website_index_document=ss["website_index_document"],
            website_error_document=ss["website_index_document"])

        bucket_origins = _cfront_origins.S3Origin(source_bucket)

        # Cloudfront distribution with S3 as origin and logging enabled

        cfront_oai = _cfront.CfnCloudFrontOriginAccessIdentity(
            self,
            "accessOriginOAI",
            cloud_front_origin_access_identity_config={
                "comment": ss["cfront_origins_comment"]
            })

        cfront_dist = _cfront.Distribution(
            self,
            ss["cfront_distribution_name"],
            default_behavior={
                "origin": bucket_origins,
                "allowed_methods": allowed_methods,
                "viewer_protocol_policy": viewer_policy
            },
            enable_ipv6=True,
            minimum_protocol_version=SecurityPolicyProtocol.TLS_V1_2_2019,
            price_class=price_class,
            default_root_object=ss["cfront_root_object"],
            comment=ss["cfront_dist_comment"],
            log_bucket=access_log_bucket,
            log_includes_cookies=False,
            log_file_prefix=ss["cfront_log_file_prefix"],
            # web_acl_id=,
            # certificate=,
            geo_restriction=GeoRestriction.whitelist(ss["geo_whitelist"]),
        )

        # Bucket policy to restrict access to bucket - Use only cloudfront's Origin Access identity
        policy_statement = _iam.PolicyStatement()
        policy_statement.add_actions('s3:GetBucket*')
        policy_statement.add_actions('s3:GetObject*')
        policy_statement.add_actions('s3:List*')
        policy_statement.add_resources(source_bucket.bucket_arn)
        policy_statement.add_resources(f"{source_bucket.bucket_arn}/*")
        policy_statement.add_canonical_user_principal(
            cfront_oai.attr_s3_canonical_user_id)
        source_bucket.add_to_resource_policy(policy_statement)

        # Outputs

        core.CfnOutput(self,
                       "CloudfrontDistribution",
                       value=(cfront_dist.distribution_domain_name))
        core.CfnOutput(self, "BucketArn", value=(source_bucket.bucket_arn))
        core.CfnOutput(self,
                       "LoggingBucketArn",
                       value=(access_log_bucket.bucket_arn))

        self.bucket = source_bucket
        self.access_logs_bucket = access_log_bucket
        self.cfront_dist = cfront_dist

    @property
    def main_source_bucket(self) -> _s3.IBucket:
        return self.bucket

    @property
    def main_access_logs_bucket(self) -> _s3.IBucket:
        return self.access_logs_bucket

    @property
    def main_cfront_dist(self) -> _cfront.IDistribution:
        return self.cfront_dist
