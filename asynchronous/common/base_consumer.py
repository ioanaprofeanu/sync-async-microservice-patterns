"""
Base consumer class for RabbitMQ message processing.
Provides error handling, logging, and graceful shutdown.
"""

import asyncio
import logging
from typing import Callable, Optional
from aio_pika import IncomingMessage
from aio_pika.abc import AbstractIncomingMessage

from rabbitmq_client import RabbitMQClient

logger = logging.getLogger(__name__)


class BaseConsumer:
    """
    Base class for RabbitMQ consumers with error handling and retry logic.
    """

    def __init__(
        self,
        queue_name: str,
        rabbitmq_client: RabbitMQClient,
        max_retries: int = 3
    ):
        """
        Initialize consumer.

        Args:
            queue_name: Queue to consume from
            rabbitmq_client: Initialized RabbitMQ client
            max_retries: Maximum retry attempts for failed messages
        """
        self.queue_name = queue_name
        self.rabbitmq_client = rabbitmq_client
        self.max_retries = max_retries
        self._running = False
        self._consumer_tag: Optional[str] = None

    async def start(self, message_handler: Callable) -> None:
        """
        Start consuming messages.

        Args:
            message_handler: Async function that processes messages
        """
        self._running = True
        logger.info(f"Starting consumer for queue: {self.queue_name}")

        try:
            await self.rabbitmq_client.consume_messages(
                queue_name=self.queue_name,
                callback=lambda message: self._handle_message(message, message_handler),
                auto_ack=False  # Manual acknowledgment for reliability
            )

            # Keep consumer running
            while self._running:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info(f"Consumer for {self.queue_name} cancelled")
            self._running = False
        except Exception as e:
            logger.error(f"Consumer error for {self.queue_name}: {e}")
            raise

    async def stop(self) -> None:
        """
        Stop consuming messages gracefully.
        """
        logger.info(f"Stopping consumer for queue: {self.queue_name}")
        self._running = False

    async def _handle_message(
        self,
        message: AbstractIncomingMessage,
        handler: Callable
    ) -> None:
        """
        Handle incoming message with error handling and retries.

        Args:
            message: Incoming RabbitMQ message
            handler: User-provided message handler function
        """
        try:
            # Decode message body
            body = message.body.decode()
            logger.debug(f"Received message from {self.queue_name}: {body[:100]}...")

            # Call user handler
            await handler(body, message)

            # Acknowledge successful processing
            await message.ack()
            logger.debug(f"Message processed successfully from {self.queue_name}")

        except asyncio.CancelledError:
            # Graceful shutdown - reject and requeue
            await message.reject(requeue=True)
            logger.info(f"Message requeued due to shutdown: {self.queue_name}")
            raise

        except Exception as e:
            # Handle processing errors
            logger.error(f"Error processing message from {self.queue_name}: {e}")

            # Check retry count
            retry_count = self._get_retry_count(message)

            if retry_count < self.max_retries:
                # Reject and requeue for retry
                await message.reject(requeue=True)
                logger.warning(
                    f"Message requeued for retry ({retry_count + 1}/{self.max_retries})"
                )
            else:
                # Max retries exceeded - send to dead letter queue or discard
                await message.reject(requeue=False)
                logger.error(
                    f"Message discarded after {self.max_retries} retries: {body[:100]}"
                )

    def _get_retry_count(self, message: AbstractIncomingMessage) -> int:
        """
        Get retry count from message headers.

        Args:
            message: Incoming message

        Returns:
            Number of retries so far
        """
        if message.headers and "x-retry-count" in message.headers:
            return int(message.headers["x-retry-count"])
        return 0


class FanoutConsumer(BaseConsumer):
    """
    Consumer for fanout exchange pattern.
    Each service creates its own queue bound to the fanout exchange.
    """

    def __init__(
        self,
        exchange_name: str,
        queue_name: str,
        rabbitmq_client: RabbitMQClient,
        max_retries: int = 3
    ):
        """
        Initialize fanout consumer.

        Args:
            exchange_name: Fanout exchange to subscribe to
            queue_name: Unique queue name for this consumer
            rabbitmq_client: RabbitMQ client
            max_retries: Max retry attempts
        """
        super().__init__(queue_name, rabbitmq_client, max_retries)
        self.exchange_name = exchange_name

    async def start(self, message_handler: Callable) -> None:
        """
        Start consuming from fanout exchange.

        Args:
            message_handler: Message processing function
        """
        # Bind queue to fanout exchange
        from aio_pika import ExchangeType
        await self.rabbitmq_client.declare_exchange(
            self.exchange_name,
            ExchangeType.FANOUT
        )
        await self.rabbitmq_client.bind_queue_to_exchange(
            queue_name=self.queue_name,
            exchange_name=self.exchange_name,
            routing_key=""  # Empty for fanout
        )

        # Start consuming
        await super().start(message_handler)
