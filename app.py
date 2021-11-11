from __future__ import annotations

import os
import pickle
import sys

from datetime import datetime
from itertools import zip_longest
from typing import Any, Iterable, Iterator, Mapping, Optional


SAVEFILE = os.path.join('saved', 'data')


def parse_data(stream: Iterable[str]) -> Iterator[Order]:
    """
    Read input and separate orders into a list of orders

    :param text: The string read from standard in
    """
    for row in stream:
        id, side, price, vol, *visible = row.strip(os.linesep).split(',')

        ordertype = BuyOrder if side == 'B' else SellOrder
        order = ordertype(
            orderid=id.strip(),
            side=side.strip(),
            price=float(price.strip()),
            volume=int(vol.strip()),
            visible=visible
        )

        yield order


def load_book(savefile: str) -> OrderBook:
    """
    Load an existing OrderBook state

    :param savefile: The path to the OrderBook saved
    """
    with open(savefile, 'rb') as f:
        return pickle.load(f)


def execute_order(
    execid: str, openid: str, price: float, volume: int) -> None:
    """
    Confirm execution of an Order and 
    print execution details to standard out

    :param execid: The OrderId of the executing order
    :param openid: The OrderId of the counterpart order
    :param price: The execution price
    :param volume: The transacted volume
    """
    sys.stdout.write(f'{os.linesep}trade {execid},{openid},{int(price)},{volume}')


class Order:
    """
    The Base class for Orders
    """
    def __init__(self, 
        orderid: Optional[str], 
        side: str, 
        price: float, 
        volume: int, **kwargs: Mapping[str, Any]) -> None:
        """
        :param orderid: Order id. None is specially reserved for terminal nodes
        :param side: Buy (B)/Sell (S)
        :param price: Limit price
        :param volume: Trade volume
        """
        self.orderid = orderid
        self.side = side
        self.price = price
        self.volume = volume
        self.prevnd = None
        self.nextnd = None
        self.ordertime = datetime.now()

        # Attributes for iceberg orders
        self._iceberg = int(*vis) if (vis := kwargs.get('visible')) else None

    @property
    def visible_volume(self) -> int:
        """
        Volume that is visible on the OrderBook
        """
        return min(self._iceberg, self.volume) if self._iceberg \
            else self.volume

    def __eq__(self, other: Order) -> bool:
        return self.price == other.price and self.ordertime == other.ordertime

    def __ne__(self, other: Order) -> bool:
        return self.price != other.price or self.ordertime != other.ordertime

    def _ordertime_priority(self, other: Order) -> int:
        """
        Return the order time priority value of this node relative to another
        Output:
            -1 if this order is newer than the other
            1 if this order is older than the other
            0 if both are equally old
        """
        if self.ordertime > other.ordertime:
            return -1
        elif self.ordertime < other.ordertime:
            return 1
        else:
            return 0

class SellOrder(Order):
    """
    Class representing a Sell order
    """
    def __init__(self, orderid: Optional[str], 
        side: str, price: float, volume: int, **kwargs) -> None:
        super().__init__(orderid, side, price, volume, **kwargs)

    def __str__(self) -> str:
        """
        String format specifications:
            price: 6 characters
            volume: 11 characters including comma separators

        No leading/trailing whitespaces. Separated by a whitespace character
        """
        return f'{format(int(self.price), "6d")} {format(self.visible_volume, "11,d")}'

    def __lt__(self, other: Order) -> bool:
        # The higher price has lower priority
        if other.price < self.price:
            return True
        
        if other.price > self.price:
            return False

        # When prices are equal, the newer order time has lower priority
        return self._ordertime_priority(other) < 0

    def __gt__(self, other: Order) -> bool:
        # The higher price has lower priority
        if other.price < self.price:
            return False
        
        if other.price > self.price:
            return True

        # When prices are equal, the newer order time has lower priority
        return self._ordertime_priority(other) > 0

    def __le__(self, other: Order) -> bool:
        # The higher price has lower priority
        if other.price < self.price:
            return True
        
        if other.price > self.price:
            return False

        # When prices are equal, the newer order time has lower priority
        return self._ordertime_priority(other) <= 0

    def __ge__(self, other: Order) -> bool:
        # The higher price has lower priority
        if other.price < self.price:
            return False
        
        if other.price > self.price:
            return True

        # When prices are equal, the newer order time has lower priority
        return self._ordertime_priority(other) >= 0


class BuyOrder(Order):
    """
    Class representing a Buy order
    """
    def __init__(self, orderid: Optional[str], 
        side: str, price: float, volume: int, **kwargs) -> None:
        super().__init__(orderid, side, price, volume, **kwargs)

    def __str__(self) -> str:
        """
        String format specifications:
            price: 6 characters
            volume: 11 characters including comma separators

        No leading/trailing whitespaces. Separated by a whitespace character
        """
        return f'{format(self.visible_volume, "11,d")} {format(int(self.price), "6d")}'

    def __lt__(self, other: Order) -> bool:
        # The higher price has higher priority
        if other.price < self.price:
            return False
        
        if other.price > self.price:
            return True

        # When prices are equal, the newer order time has lower priority
        return self._ordertime_priority(other) < 0

    def __gt__(self, other: Order) -> bool:
        # The higher price has higher priority
        if other.price < self.price:
            return True
        
        if other.price > self.price:
            return False

        # When prices are equal, the newer order time has lower priority
        return self._ordertime_priority(other) > 0

    def __le__(self, other: Order) -> bool:
        # The higher price has higher priority
        if other.price < self.price:
            return False
        
        if other.price > self.price:
            return True

        # When prices are equal, the newer order time has lower priority
        return self._ordertime_priority(other) <= 0

    def __ge__(self, other: Order) -> bool:
        # The higher price has higher priority
        if other.price < self.price:
            return True
        
        if other.price > self.price:
            return False

        # When prices are equal, the newer order time has lower priority
        return self._ordertime_priority(other) >= 0


class OrderBook:
    """
    The Order Book is responsible for:
        1. Execute trades
        2. Maintain open orders in price time priority
        3. Prints trade execution (if any) to standard out
        4. Prints open orders before exiting
    """
    def __init__(self, savefile: str) -> None:
        """
        :param savefile: Path to the save file
        """
        self.buy_head = Order(None, 'B', float('-inf'), 0)
        self.sell_head = Order(None, 'S', float('inf'), 0)
        self.effectivebid = float('inf')
        self.effectiveask = float('-inf')
        self.savefile = savefile

    def __str__(self) -> str:
        """
        OrderBook stdout specifications
            (Buyers)              (Sellers)
        000,000,000 000000 | 000000 000,000,000
        """
        _out = f'{os.linesep}'
        for x, y in zip_longest(
            self.fetch_orders('B'), 
            self.fetch_orders('S'), fillvalue=' ' * 18):
            _out += f'{x} | {y}{os.linesep}'

        return _out

    def fetch_orders(self, side: str) -> Iterator[Order]:
        """
        Return an iterator of Orders given specified side

        :param side: Buy (B)/ Sell (S)
        """
        if side not in ['B', 'S']:
            return []

        nd = self.buy_head if side == 'B' else self.sell_head
        while nd.nextnd:
            # Only yield the node if it is not the terminal node
            yield nd

            nd = nd.nextnd


    def serialize_state(self) -> None:
        """
        Serialize states if there are open orders left
        """
        raise NotImplementedError

    def process_orders(self, data: Iterable[Order]) -> None:
        """
        Execute Buy/Sell orders. Add unexecuted orders to the book

        :param data: List of incoming Orders
        """
        for order in data:
            if order.side == 'B' and order.price >= self.effectiveask:
                order = self._process_buy(order)
            elif order.side == 'S' and order.price <= self.effectivebid:
                order = self._process_sell(order)

            if order.volume:
                # Add balance orders to the book if any
                self.add_to_book(order)

    def _process_buy(self, order: Order) -> Order:
        """
        Process a Buy order. Update the order volume and return it

        :param order: An instance of Order
        """
        nd = self.sell_head
        while nd.nextnd and nd.price <= order.price:
            # Execute the Buy if there is an open Sell with lower price
            balance = max(order.volume - nd.volume, 0)

            if not balance:
                # Order filled completely, confirm execution
                execute_order(
                    order.orderid, nd.orderid, nd.price, order.volume)
            else:
                # Order filled only partially, confirm execution
                execute_order(
                    order.orderid, nd.orderid, nd.price, nd.volume)

            # Update the executing order and the open order
            nd.volume = max(nd.volume - order.volume, 0)
            order.volume = balance

            # If leading sell Order is filled, remove it.
            if not nd.volume:
                self.sell_head = nd.nextnd
                self.sell_head.prevnd = None
                self.effectiveask = self.sell_head.price
                nd = nd.nextnd

            if not order.volume:
                break

        return order

    def _process_sell(self, order: Order) -> Order:
        """
        Process a Sell order. Update the order volume and return it

        :param order: An instance of Order
        """
        nd = self.buy_head

        while nd.nextnd and nd.price >= order.price:
            # Execute the Sell if there is an open Buy with higher price
            balance = max(order.volume - nd.volume, 0)

            if not balance:
                # Order filled completely, confirm execution
                execute_order(
                    order.orderid, nd.orderid, nd.price, order.volume)
            else:
                # Order filled only partially, confirm execution
                execute_order(
                    order.orderid, nd.orderid, nd.price, nd.volume)

            # Update the executing order and the open order
            nd.volume = max(nd.volume - order.volume, 0)
            order.volume = balance

            # If leading buy Order is filled, remove it
            if not nd.volume:
                self.buy_head = nd.nextnd
                self.buy_head.prevnd = None
                self.effectivebid = self.buy_head.price
                nd = nd.nextnd

            if not order.volume:
                break

        return order

    def add_to_book(self, order: Order) -> None:
        """
        Add an open order to the book

        :param order: An instance of Order
        """
        side = order.side
        for nd in self.fetch_orders(side):
            # Keep looking until encounter a node with lower priority
            # Terminal nodes will always have the lowest priority
            if order <= nd:
                continue
            
            order.prevnd = nd.prevnd
            nd.prevnd = order
            order.nextnd = nd

            break
        else:
            # Only in-scope when the chain consists of only terminal nodes
            prevhead = self.buy_head if side == 'B' else self.sell_head

            prevhead.prevnd = order
            order.nextnd = prevhead

        if not order.prevnd:
            # The order is now the new head
            if order.side == 'B':
                self.buy_head = order
                self.effectivebid = order.price
            else:
                self.sell_head = order
                self.effectiveask = order.price
        else:
            # Link the higher priority node to this order
            order.prevnd.nextnd = order

    def save(self):
        """
        Save the state of the OrderBook to local disk
        """
        with open(self.savefile, 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)


def main() -> None:
    """
    Application entry point
    """
    book = OrderBook(SAVEFILE)
    # Checks local filesystem for saved state and load OrderBook if exists
    if os.path.isfile(SAVEFILE):
        book = load_book(SAVEFILE)

    book.process_orders(parse_data(sys.stdin))
    book.save()
    print(book)


if __name__ == '__main__':
    main()