from aws_cdk import (
    core,
    aws_iam as _iam,
    aws_sqs as _sqs
)

from aws_cdk.core import (Duration, RemovalPolicy)

class QueueConstruct(core.Construct):

    def __init__(self, scope: core.Construct, construct_id: str, queue_context: str,  **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        q = dict(self.node.try_get_context(queue_context))

        queueDlq = _sqs.Queue(
            self,
            q["queue_dlq_name"],
            queue_name=q["queue_dlq_name"]
        )

        queue = _sqs.Queue(
            self,
            q["queue_name"],
            queue_name=q["queue_name"],
            dead_letter_queue=_sqs.DeadLetterQueue(
                max_receive_count=q["queue_dlq_max_receive_count"],
                queue=queueDlq
            ),
            encryption=_sqs.QueueEncryption.KMS_MANAGED,
            visibility_timeout=Duration.seconds(30),
            delivery_delay=Duration.seconds(15),
            retention_period=Duration.hours(14),
        )

        self.queue = queue
        self.queue_dlq = queueDlq

        # Outputs

        core.CfnOutput(
            self,
            "QueueUrl",
            value=(queue.queue_url)
        )

    @property
    def main_queue(self) -> _sqs.IQueue:
        return self.queue

    @property
    def main_queue_dlq(self) -> _sqs.IQueue:
        return self.queue_dlq
