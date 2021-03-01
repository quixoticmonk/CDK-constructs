from aws_cdk import (
    aws_lambda as _lambda,
    aws_apigateway as _api_gw,
    aws_dynamodb as _ddb,
    aws_sns as sns,
    aws_cloudwatch as cloud_watch,
    aws_cloudwatch_actions as actions,
    core
)
import jsii


class CloudwatchDashboardConstruct(core.Construct):

    def __init__(self, scope: core.Construct, id: str, stage: str, api: _api_gw.IRestApi, fn: _lambda.IFunction, table: _ddb.ITable,   **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        gw = dict(self.node.try_get_context("gateway"))

        ###
        # Custom Metrics
        ###

        # Gather the % of lambda invocations that error in past 5 mins
        lambda_error_perc = cloud_watch.MathExpression(expression="e / i * 100",
                                                       label="% of invocations that errored, last 5 mins",
                                                       using_metrics={
                                                           "i": fn.metric(metric_name="Invocations",
                                                                          statistic="sum"),
                                                           "e": fn.metric(metric_name="Errors",
                                                                          statistic="sum"),
                                                       },
                                                       period=core.Duration.minutes(5))

        # note: throttled requests are not counted in total num of invocations
        lambda_throttled_perc = cloud_watch.MathExpression(expression="t / (i + t) * 100",
                                                           label="% of throttled requests, last 30 mins",
                                                           using_metrics={
                                                               "i": fn.metric(metric_name="Invocations",
                                                                              statistic="sum"),
                                                               "t": fn.metric(metric_name="Throttles",
                                                                              statistic="sum"),
                                                           },
                                                           period=core.Duration.minutes(5))

        dashboard = cloud_watch.Dashboard(
            self,
            id="CloudWatchDashBoard",
            dashboard_name="Serverlesslens"
        )

        dashboard.add_widgets(cloud_watch.GraphWidget(title="Requests",
                                                      width=8,
                                                      left=[self.metric_for_api_gw(api_name=gw["gw_name"],
                                                                                   stage=stage,
                                                                                   metric_name="Count",
                                                                                   label="# Requests",
                                                                                   stat="sum")]),
                              cloud_watch.GraphWidget(title="API GW Latency",
                                                      width=8,
                                                      stacked=True,
                                                      left=[self.metric_for_api_gw(api_name=gw["gw_name"],
                                                                                   stage=stage,
                                                                                   metric_name="Latency",
                                                                                   label="API Latency p50",
                                                                                   stat="p50"),
                                                            self.metric_for_api_gw(api_name=gw["gw_name"],
                                                                                   stage=stage,
                                                                                   metric_name="Latency",
                                                                                   label="API Latency p90",
                                                                                   stat="p90"),
                                                            self.metric_for_api_gw(api_name=gw["gw_name"],
                                                                                   stage=stage,
                                                                                   metric_name="Latency",
                                                                                   label="API Latency p99",
                                                                                   stat="p99")
                                                            ]),
                              cloud_watch.GraphWidget(title="API GW Errors",
                                                      width=8,
                                                      stacked=True,
                                                      left=[self.metric_for_api_gw(api_name=gw["gw_name"],
                                                                                   stage=stage,
                                                                                   metric_name="4XXError",
                                                                                   label="4XX Errors",
                                                                                   stat="sum"),
                                                            self.metric_for_api_gw(api_name=gw["gw_name"],
                                                                                   stage=stage,
                                                                                   metric_name="5XXError",
                                                                                   label="5XX Errors",
                                                                                   stat="sum")
                                                            ]),
                              cloud_watch.GraphWidget(title="Dynamo Lambda Error %",
                                                      width=8,
                                                      left=[lambda_error_perc]),
                              cloud_watch.GraphWidget(title="Dynamo Lambda Duration",
                                                      width=8,
                                                      stacked=True,
                                                      left=[fn.metric_duration(statistic="p50"),
                                                            fn.metric_duration(
                                                                statistic="p90"),
                                                            fn.metric_duration(statistic="p99")]),
                              cloud_watch.GraphWidget(title="Dynamo Lambda Throttle %",
                                                      width=8,
                                                      left=[lambda_throttled_perc]),
                              cloud_watch.GraphWidget(title="DynamoDB Latency",
                                                      width=8,
                                                      stacked=True,
                                                      left=[table.metric_successful_request_latency(
                                                          dimensions={"TableName": table.table_name,
                                                                      "Operation": "GetItem"}),
                                                            table.metric_successful_request_latency(
                                                          dimensions={"TableName": table.table_name,
                                                                      "Operation": "UpdateItem"}),
                                                            table.metric_successful_request_latency(
                                                          dimensions={"TableName": table.table_name,
                                                                      "Operation": "PutItem"}),
                                                            table.metric_successful_request_latency(
                                                          dimensions={"TableName": table.table_name,
                                                                      "Operation": "DeleteItem"}),
                                                            table.metric_successful_request_latency(
                                                          dimensions={"TableName": table.table_name,
                                                                      "Operation": "Query"}),
                                                            ]),
                              cloud_watch.GraphWidget(title="DynamoDB Consumed Read/Write Units",
                                                      width=8,
                                                      stacked=False,
                                                      left=[table.metric(metric_name="ConsumedReadCapacityUnits"),
                                                            table.metric(metric_name="ConsumedWriteCapacityUnits")]),
                              cloud_watch.GraphWidget(title="DynamoDB Throttles",
                                                      width=8,
                                                      stacked=True,
                                                      left=[table.metric(metric_name="ReadThrottleEvents",
                                                                         statistic="sum"),
                                                            table.metric(metric_name="WriteThrottleEvents",
                                                                         statistic="sum")]),
                              )

    @jsii.implements(cloud_watch.IMetric)
    def metric_for_api_gw(self, api_name: str, stage: str, metric_name: str,  label: str, stat: str = 'avg'):
        return self.build_metric(metric_name, "AWS/ApiGateway", {"ApiName": api_name, "Stage": stage},  cloud_watch.Unit.COUNT, label, stat)

    @staticmethod
    def build_metric(metric_name: str, name_space: str, dimensions, unit: cloud_watch.Unit, label: str,
                     stat: str = 'avg', period: int = 900):
        return cloud_watch.Metric(metric_name=metric_name,
                                  namespace=name_space,
                                  dimensions=dimensions,
                                  unit=unit,
                                  label=label,
                                  statistic=stat,
                                  period=core.Duration.seconds(period))
