from taskiq import TaskiqEvents, TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from src.settings import REDIS_URL

broker = ListQueueBroker(REDIS_URL).with_result_backend(
    RedisAsyncResultBackend(REDIS_URL)
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_startup(state: TaskiqState) -> None:
    from libs.pb_client import start_pb
    from src.brands import registry
    await start_pb()
    registry.load()
