import asyncio
from dataclasses import dataclass


class InvalidToken(Exception):
    pass


@dataclass
class Queues:
    messages_queue: asyncio.queues.Queue
    saving_queue: asyncio.queues.Queue
    sending_queue: asyncio.queues.Queue
    status_queue: asyncio.queues.Queue
    watchdog_queue: asyncio.queues.Queue


class ReconnectsCount:
    def __init__(self, max_reconnects, downtime):
        self.count = 0
        self.max_reconnects = max_reconnects
        self.downtime = downtime

    def reset(self):
        self.count = 0

    def increment(self):
        self.count += 1

    def overpassed_max_reconnects_amount(self):
        return self.count >= self.max_reconnects

    def get_idle_time(self):
        return (self.count - self.max_reconnects) * self.downtime
