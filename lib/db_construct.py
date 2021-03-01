from aws_cdk import (
    core,
    aws_iam as _iam,
    aws_dynamodb as _ddb,
    aws_cloudwatch as _cwlogs,
    aws_logs as _logs,
    aws_sqs as _sqs,
    aws_lambda as _lambda
)

from aws_cdk.aws_dynamodb import (
    BillingMode,
    Table,
    Attribute,
    AttributeType,
    ITable,
    ProjectionType

)


class DbConstruct(core.Construct):

    def __init__(self, scope: core.Construct, construct_id: str, db_context: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # setting the db context
        db = dict(self.node.try_get_context(db_context))

        # Shortening some of the logic
        billing_mode = BillingMode.PROVISIONED if db[
            "db_billing_mode"] == "provisioned" else BillingMode.PAY_PER_REQUEST
        pk = db["db_table_pk"]
        pk_type = AttributeType.STRING if db["db_table_pk_type"] == "string" else AttributeType.NUMBER
        sk = None if db["db_table_sk"] == "" else db["db_table_sk"]
        sk_type = AttributeType.STRING if db["db_table_sk_type"] == "string" else AttributeType.NUMBER
        gsi_projection_type = ProjectionType.ALL if db[
            "db_gsi_projection"] == "all" else ProjectionType.KEYS_ONLY
        lsi_projection_type = ProjectionType.ALL if db[
            "db_lsi_projection"] == "all" else ProjectionType.KEYS_ONLY

        if(sk):
            table = Table(
                self,
                db["db_table"],
                table_name=db["db_table"],
                partition_key=Attribute(
                    name=pk, type=pk_type),
                sort_key=Attribute(
                    name=sk, type=sk_type),
                read_capacity=db["db_min_read_capacity"],
                write_capacity=db["db_min_write_capacity"],
                encryption=_ddb.TableEncryption.AWS_MANAGED,
                point_in_time_recovery=True,
                removal_policy=core.RemovalPolicy.DESTROY,
                billing_mode=billing_mode,
            )
        else:
            table = Table(
                self,
                db["db_table"],
                table_name=db["db_table"],
                partition_key=Attribute(
                    name=pk, type=pk_type),
                read_capacity=db["db_min_read_capacity"],
                write_capacity=db["db_min_write_capacity"],
                encryption=_ddb.TableEncryption.AWS_MANAGED,
                point_in_time_recovery=True,
                removal_policy=core.RemovalPolicy.DESTROY,
                billing_mode=billing_mode,
            )

        # Add read/write autoscaling enabled at X% utilization
        if(db["db_billing_mode"] == "provisioned" and db["db_enable_autoscaling"]):
            read_scaling = table.auto_scale_read_capacity(
                min_capacity=db["db_min_read_capacity"],
                max_capacity=db["db_max_read_capacity"],
            )

            read_scaling.scale_on_utilization(
                target_utilization_percent=db["db_target_utilization"],
            )
            write_scaling = table.auto_scale_write_capacity(
                min_capacity=db["db_min_write_capacity"],
                max_capacity=db["db_max_write_capacity"],
            )
            write_scaling.scale_on_utilization(
                target_utilization_percent=db["db_target_utilization"],
            )

        # setting projection with keys or all

        if(db["db_reverse_index"] and sk):
            table.add_global_secondary_index(
                partition_key=Attribute(
                    name=sk, type=sk_type),
                sort_key=_ddb.Attribute(
                    name=pk, type=pk_type),
                read_capacity=db["db_min_read_capacity"],
                write_capacity=db["db_min_write_capacity"],
                index_name='reverseIndex',
                projection_type=gsi_projection_type,
            )
            table.auto_scale_global_secondary_index_read_capacity(
                index_name='reverseIndex',
                min_capacity=db["db_min_read_capacity"],
                max_capacity=db["db_max_read_capacity"],
            )
            table.auto_scale_global_secondary_index_write_capacity(
                index_name='reverseIndex',
                min_capacity=db["db_min_write_capacity"],
                max_capacity=db["db_max_write_capacity"],
            )
        else:
            print("No Reverse indexes created")

        # Add LSI with a projection of All
        if(db["db_add_lsi"]):
            table.add_local_secondary_index(
                index_name='LSI1',
                projection_type=lsi_projection_type,
                sort_key=Attribute(
                    name='LSISK', type=AttributeType.STRING),
            )

        self.table = table

    @property
    def main_table(self) -> ITable:
        return self.table
