import argparse
import asyncio
import random
from abc import ABC
from datetime import datetime, timedelta
from decimal import Decimal
from json import load
from sys import stdin
from typing import Coroutine


def log(data: str) -> None:
    print(f"[{datetime.now()}] {data}")


class Courier:
    def __init__(self, courier_manager, id: str, delay: int, order):
        self.courier_manager = courier_manager
        self.id = id
        self.delay = delay
        self.order = order
        self.arrived_at = None
        self.order_wait_time = Decimal("0")
        self.courier_wait_time = Decimal("0")

    def __str__(self):
        return f"Courier #{self.id}"

    async def dispatch(self) -> Coroutine:
        log(
            f"{self} will arrive in {self.delay} seconds to pick up {self.order if self.order else 'the next order'}"
        )
        await asyncio.sleep(self.delay)
        self.arrived_at = datetime.now()
        log(f"{self} has arrived")

    async def wait_for_order_to_be_ready(self) -> Coroutine:
        if not self.order:
            # FIFO
            log(f"{self}: Waiting for the next order")
            self.order = await self.courier_manager.order_manager.get_next_order(self.id)
            log(
                f"{self}: Picked up {self.order}, waited {self.get_wait_time():.0f} ms, while the order waited for {self.get_order_wait_time():.0f} ms"
            )

            return

        # Matched
        log(f"{self}: Waiting for {self.order} to be ready")
        while not self.order.ready_at:
            await asyncio.sleep(0.1)

        log(
            f"{self}: Picked up {self.order}, waited {self.get_wait_time():.0f} ms, while the order waited for {self.get_order_wait_time():.0f} ms"
        )

    def get_wait_time(self):
        if self.arrived_at < self.order.ready_at:
            return Decimal(
                (self.order.ready_at - self.arrived_at) / timedelta(milliseconds=1)
            )

        return Decimal(0)

    def get_order_wait_time(self):
        if self.arrived_at < self.order.ready_at:
            return Decimal(0)

        return Decimal(
            (self.arrived_at - self.order.ready_at) / timedelta(milliseconds=1)
        )


class CourierManager(ABC):
    def __init__(self) -> None:
        self.order_manager = None
        self.couriers = {}
        self.order_wait_times = []
        self.courier_wait_times = []

    async def _dispatch(self, order):
        courier = Courier(
            self,
            1 + len(self.couriers.keys()),
            random.randint(3, 15),
            order,
        )
        self.couriers[courier.id] = courier

        await courier.dispatch()
        await courier.wait_for_order_to_be_ready()
        self.collect_stats(courier)

        return courier

    def collect_stats(self, courier):
        self.courier_wait_times.append(courier.get_wait_time())
        self.order_wait_times.append(courier.get_order_wait_time())

        average_courier_wait_time, average_order_wait_time = self.get_averages()
        log(f"{self}: Average food wait time: {average_order_wait_time:.0f} milliseconds")
        log(
            f"{self}: Average courier wait time: {average_courier_wait_time:.0f} milliseconds"
        )

    def get_averages(self):
        average_courier_wait_time = sum(self.courier_wait_times) / len(
            self.courier_wait_times
        )
        average_order_wait_time = sum(self.order_wait_times) / len(self.order_wait_times)
        return average_courier_wait_time, average_order_wait_time


class MatchedCourierManager(CourierManager):
    def __str__(self) -> str:
        return "MatchedCourierManager"

    async def dispatch(self, order):
        await self._dispatch(order)


class FifoCourierManager(CourierManager):
    def __str__(self) -> str:
        return "FifoCourierManager"

    async def dispatch(self, order):
        await self._dispatch(None)


class Order:
    def __init__(self, id: str, name: str, prepTime: int):
        self.order_manager = None
        self.id = id
        self.name = name
        self.prep_time = prepTime
        self.ready_at = None
        self.courier_id = None

    def __str__(self):
        return f"Order #{self.id.upper()[:8]} {self.name}"

    async def prepare(self) -> Coroutine:
        log(f"{self}: Preparing in {self.prep_time} seconds")
        await asyncio.sleep(self.prep_time)
        self.ready_at = datetime.now()
        log(f"{self}: Ready for courier")


class OrderManager:
    def __init__(self, courier_manager) -> None:
        self.courier_manager = courier_manager
        self.courier_manager.order_manager = self
        self.orders = {}
        self.results = []

    def __str__(self) -> str:
        return "OrderManager"

    async def prepare(self, order: Order):
        order.order_manager = self
        self.orders[order.id] = order

        await asyncio.gather(
            order.prepare(),
            self.courier_manager.dispatch(order),
        )

    async def get_next_order(self, courier_id: str) -> Coroutine:
        while True:
            await asyncio.sleep(0.1)
            for order in self.orders.values():
                if order.ready_at and order.courier_id is None:
                    order.courier_id = courier_id

                    return order


async def main(args):
    random.seed(args.seed)
    strategies = {
        "matched": MatchedCourierManager,
        "fifo": FifoCourierManager,
    }
    courier_manager = strategies[args.strategy]()

    order_manager = OrderManager(courier_manager)

    order_coroutines = []
    orders_data = load(stdin)
    while True:
        if len(orders_data) == 0:
            break

        await asyncio.sleep(1)
        log("Main: Tick")
        order_coroutines.extend(
            [
                asyncio.create_task(
                    order_manager.prepare(
                        Order(**order_data),
                    ),
                )
                for order_data in orders_data[:2]
            ]
        )
        del orders_data[:2]

    await asyncio.gather(*order_coroutines)
    average_courier_wait_time, average_order_wait_time = courier_manager.get_averages()
    log(f"Main: Average food wait time: {average_order_wait_time:.0f} milliseconds")
    log(f"Main: Average courier wait time: {average_courier_wait_time:.0f} milliseconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--strategy", type=str, default="matched")
    parser.add_argument("-d", "--seed", type=int, default=777)
    loop = asyncio.get_event_loop()
    asyncio.run(main(parser.parse_args()))
