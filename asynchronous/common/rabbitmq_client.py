"""
Shared RabbitMQ connection handler with reconnection logic.
This module provides async connection management for all microservices.
"""

import asyncio
import logging
from typing import Optional, Callable
import aio_pika
from aio_pika import Connection, Channel, Exchange, Queue, ExchangeType
from aio_pika.abc import AbstractRobustConnection

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """
    Async RabbitMQ client with automatic reconnection and connection pooling.
    """

    def __init__(
        self,
        host: str = "rabbitmq",
        port: int = 5672,
        user: str = "guest",
        password: str = "guest",
        virtualhost: str = "/"
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.virtualhost = virtualhost
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel: Optional[Channel] = None

    async def connect(self) -> None:
        """
        Establish connection to RabbitMQ with automatic reconnection.
        """
        try:
            connection_url = f"amqp://{self.user}:{self.password}@{self.host}:{self.port}{self.virtualhost}"
            self.connection = await aio_pika.connect_robust(
                connection_url,
                timeout=30,
                reconnect_interval=5,
            )
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)  # Limit concurrent messages
            logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self) -> None:
        """
        Close RabbitMQ connection gracefully.
        """
        try:
            if self.channel:
                await self.channel.close()
            if self.connection:
                await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")

    async def declare_queue(
        self,
        queue_name: str,
        durable: bool = True,
        auto_delete: bool = False
    ) -> Queue:
        """
        Declare a queue (creates if doesn't exist).

        Args:
            queue_name: Name of the queue
            durable: Queue survives broker restart
            auto_delete: Queue is deleted when last consumer unsubscribes

        Returns:
            Queue object
        """
        if not self.channel:
            raise RuntimeError("Channel not initialized. Call connect() first.")

        queue = await self.channel.declare_queue(
            queue_name,
            durable=durable,
            auto_delete=auto_delete
        )
        logger.info(f"Declared queue: {queue_name}")
        return queue

    async def declare_exchange(
        self,
        exchange_name: str,
        exchange_type: ExchangeType = ExchangeType.DIRECT,
        durable: bool = True
    ) -> Exchange:
        """
        Declare an exchange.

        Args:
            exchange_name: Name of the exchange
            exchange_type: Type (DIRECT, FANOUT, TOPIC, HEADERS)
            durable: Exchange survives broker restart

        Returns:
            Exchange object
        """
        if not self.channel:
            raise RuntimeError("Channel not initialized. Call connect() first.")

        exchange = await self.channel.declare_exchange(
            exchange_name,
            exchange_type,
            durable=durable
        )
        logger.info(f"Declared exchange: {exchange_name} (type: {exchange_type.value})")
        return exchange

    async def publish_message(
        self,
        exchange_name: str,
        routing_key: str,
        message_body: str,
        exchange_type: ExchangeType = ExchangeType.DIRECT
    ) -> None:
        """
        Publish a message to an exchange.

        Args:
            exchange_name: Target exchange (empty string for default exchange)
            routing_key: Routing key (queue name for direct exchange)
            message_body: JSON string message
            exchange_type: Exchange type
        """
        if not self.channel:
            raise RuntimeError("Channel not initialized. Call connect() first.")

        # Handle default exchange (empty string) - don't declare it
        if exchange_name == "":
            # Use channel's default exchange
            exchange = self.channel.default_exchange
        else:
            exchange = await self.declare_exchange(exchange_name, exchange_type)

        message = aio_pika.Message(
            body=message_body.encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # Survive broker restart
            content_type="application/json"
        )

        await exchange.publish(message, routing_key=routing_key)
        logger.debug(f"Published message to {exchange_name or 'default'}/{routing_key}")

    async def consume_messages(
        self,
        queue_name: str,
        callback: Callable,
        auto_ack: bool = False
    ) -> None:
        """
        Start consuming messages from a queue.

        Args:
            queue_name: Queue to consume from
            callback: Async function to handle messages
            auto_ack: Automatically acknowledge messages
        """
        if not self.channel:
            raise RuntimeError("Channel not initialized. Call connect() first.")

        queue = await self.declare_queue(queue_name)

        logger.info(f"Starting consumer on queue: {queue_name}")
        await queue.consume(callback, no_ack=auto_ack)

    async def bind_queue_to_exchange(
        self,
        queue_name: str,
        exchange_name: str,
        routing_key: str = ""
    ) -> Queue:
        """
        Bind a queue to an exchange with a routing key.

        Args:
            queue_name: Queue to bind
            exchange_name: Exchange to bind to
            routing_key: Routing key (empty for fanout)

        Returns:
            Queue object
        """
        if not self.channel:
            raise RuntimeError("Channel not initialized. Call connect() first.")

        queue = await self.declare_queue(queue_name)
        exchange = await self.channel.get_exchange(exchange_name)

        await queue.bind(exchange, routing_key=routing_key)
        logger.info(f"Bound queue {queue_name} to exchange {exchange_name} with routing key '{routing_key}'")

        return queue
