from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend
from src.config import REDIS_URL

broker = ListQueueBroker(REDIS_URL).with_result_backend(
    RedisAsyncResultBackend(REDIS_URL)
)