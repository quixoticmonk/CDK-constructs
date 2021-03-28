from aws_cdk import (
    core,
    aws_lambda as _lambda,
    aws_apigateway as _api_gw,
    aws_logs as _logs,
)

from aws_cdk.aws_apigateway import (MethodLoggingLevel, EndpointType,
                                    AccessLogFormat, LogGroupLogDestination,
                                    JsonSchemaVersion, JsonSchemaType,
                                    MethodResponse, PassthroughBehavior)

LOG_INFO = MethodLoggingLevel.INFO
LOG_ERROR = MethodLoggingLevel.ERROR
LOG_RETENTION_PERIOD = _logs.RetentionDays.ONE_WEEK


class ApiLambdaIntegationRestConstruct(core.Construct):
    def __init__(self, scope: core.Construct, construct_id: str, stage: str,
                 lambda_fn_alias: _lambda.IAlias, gw_context: str,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        gw = dict(self.node.try_get_context(gw_context))

        # # api gateway log groups

        api_log_group = _logs.LogGroup(
            self,
            gw["gw_log_group_name"],
            log_group_name="/aws/apigateway/" + gw["gw_log_group_name"],
            retention=LOG_RETENTION_PERIOD,
            removal_policy=core.RemovalPolicy.DESTROY)

        # # api gateway to handle post requests
        gateway = _api_gw.RestApi(
            self,
            gw["gw_name"],
            rest_api_name=gw["gw_name"],
            deploy_options={
                "description":
                gw["gw_stage_description"],
                "logging_level":
                LOG_INFO,
                "tracing_enabled":
                True,
                "stage_name":
                stage,
                "access_log_destination":
                LogGroupLogDestination(api_log_group),
                "access_log_format":
                AccessLogFormat.json_with_standard_fields(caller=False,
                                                          http_method=True,
                                                          ip=True,
                                                          protocol=True,
                                                          request_time=True,
                                                          resource_path=True,
                                                          response_length=True,
                                                          status=True,
                                                          user=True),
                "metrics_enabled":
                True,
            },
            endpoint_configuration={
                "types": [
                    EndpointType.REGIONAL if gw["gw_endpoint_type"]
                    == "regional" else EndpointType.EDGE
                ]
            },
            deploy=True,
            cloud_watch_role=True,
            description=gw["gw_description"],
        )

        # Response modesls are neded for a non-proxy integration
        response_model = gateway.add_model(
            gw["gw_response_model_name"],
            content_type="application/json",
            model_name=gw["gw_response_model_name"],
            schema={
                "schema": JsonSchemaVersion.DRAFT4,
                "title": gw["gw_response_model_name"],
                "type": JsonSchemaType.OBJECT,
                "properties": {
                    "message": {
                        "type": JsonSchemaType.STRING
                    }
                }
            })

        error_response_model = gateway.add_model(
            gw["gw_error_response_model_name"],
            content_type="application/json",
            model_name=gw["gw_error_response_model_name"],
            schema={
                "schema": JsonSchemaVersion.DRAFT4,
                "title": gw["gw_error_response_model_name"],
                "type": JsonSchemaType.OBJECT,
                "properties": {
                    "state": {
                        "type": JsonSchemaType.STRING
                    },
                    "message": {
                        "type": JsonSchemaType.STRING
                    }
                }
            })

        # Setting passthrough behavior
        pass_context = gw["gw_passthrough_behavior"]

        passthrough_behavior = PassthroughBehavior.WHEN_NO_TEMPLATES if pass_context == "WHEN_NO_TEMPLATES" else PassthroughBehavior.WHEN_NO_MATCH if pass_context == "WHEN_NO_MATCH" else PassthroughBehavior.NEVER

        lambda_integration = _api_gw.LambdaIntegration(
            lambda_fn_alias,
            proxy=False,
            passthrough_behavior=passthrough_behavior,
        )

        gateway_root_resource = gateway.root.add_resource(
            gw["gw_root_resource"])

        gateway_post_method = gateway_root_resource.add_method(
            gw["gw_method"],
            lambda_integration,
            api_key_required=True,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': response_model}),
                MethodResponse(
                    status_code='400',
                    response_models={'application/json':
                                     error_response_model}),
            ])

        gateway_root_resource.add_cors_preflight(
            allow_origins=[gw["gw_origins_cors"]],
            allow_methods=[gw["gw_origins_cors_method"]])

        gateway_post_key = gateway.add_api_key(
            gw["gw_api_key_name"],
            api_key_name=gw["gw_api_key_name"],
        )

        api_key_usage_plan = gateway.add_usage_plan(
            gw["gw_api_key_usage_plan_name"],
            name=gw["gw_api_key_usage_plan_name"],
            api_key=gateway_post_key,
            throttle={
                "rate_limit": gw["gw_api_key_usage_throttle"],
                "burst_limit": gw["gw_api_key_usage_burst"],
            },
        )

        api_key_usage_plan.add_api_stage(
            stage=gateway.deployment_stage,
            throttle=[{
                "method": gateway_post_method,
                "throttle": {
                    "rate_limit": gw["gw_api_key_usage_throttle"],
                    "burst_limit": gw["gw_api_key_usage_burst"],
                }
            }])
        # # Outputs

        core.CfnOutput(self, "ApiGwUrl", value=(gateway.url))

        core.CfnOutput(self,
                       "ApiGWLogGroup",
                       value=(api_log_group.log_group_name))

        self.apigw = gateway

    @property
    def main_api(self) -> _api_gw.IRestApi:
        return self.apigw
