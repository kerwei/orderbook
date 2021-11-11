import os
import time
import unittest

from app import BuyOrder, SAVEFILE, SellOrder, OrderBook, parse_data, load_book


TESTDIR = os.path.join('tests')
TESTSAVEFILE = os.path.join(TESTDIR, 'data')


class TestParseInput(unittest.TestCase):
    def setUp(self) -> None:
        self.test_filepath = os.path.join(TESTDIR, 'test1.txt')

    def testReadStdIn(self) -> None:
        """
        Input should read the correct number of lines
        """
        with open(self.test_filepath, 'r') as f:
            data = [ln for ln in f.readlines()]

        data_in = parse_data(data)
        self.assertEqual(len([d for d in data_in]), 6)


class TestBuySellOrder(unittest.TestCase):
    def testHigherPricePrioritySellOrder(self):
        """
        high > low because of lower price
        """
        high = SellOrder('1', 'S', 100, 1000)
        low = SellOrder('1', 'S', 200, 1000)

        self.assertLess(low, high)

    def testHigherTimePrioritySellOrder(self):
        """
        high > low because of older timestamp
        """
        high = SellOrder('1', 'S', 100, 1000)
        time.sleep(0.01)
        low = SellOrder('1', 'S', 100, 1000)

        self.assertLess(low, high)

    def testHigherPricePriorityBuyOrder(self):
        """
        high > low because of lower price
        """
        low = BuyOrder('1', 'B', 100, 1000)
        high = BuyOrder('1', 'B', 200, 1000)

        self.assertLess(low, high)

    def testHigherTimePriorityBuyOrder(self):
        """
        high > low because of older timestamp
        """
        high = BuyOrder('1', 'B', 100, 1000)
        time.sleep(0.01)
        low = BuyOrder('1', 'B', 100, 1000)

        self.assertLess(low, high)

    def testSellOrderStdOutFormat(self):
        """
        Sell output string needs to adhere to expected standard
        """
        order = SellOrder('1', 'S', 100, 1000)
        self.assertEqual(
            str(order),
            '   100       1,000')

    def testBuyOrderStdOutFormat(self):
        """
        Buy output string needs to adhere to expected standard
        """
        order = BuyOrder('1', 'B', 100, 1000)
        self.assertEqual(
            str(order),
            '      1,000    100')


class TestOrderBook(unittest.TestCase):
    def setUp(self) -> None:
        """
        Instantiate an OrderBook and process parsed input Buy/Sell data
        """
        test_filepath = os.path.join(TESTDIR, 'test1.txt')

        with open(test_filepath, 'r') as f:
            data = [ln for ln in f.readlines()]
        
        self.book = OrderBook(TESTSAVEFILE)
        self.book.process_orders(parse_data(data))

    def tearDown(self) -> None:
        """
        Remove the save file if it was created
        """
        # print(f'{os.linesep}{self._testMethodName} Bid: {self.book.effectivebid} Ask {self.book.effectiveask}')
        if os.path.isfile(TESTSAVEFILE):
            os.remove(TESTSAVEFILE)

    def testLengthOfBuyList(self):
        """
        OrderBook must have the correct number of Buy orders
        """
        lst_buy = self.book.fetch_orders('B')
        self.assertEqual(len([b for b in lst_buy]), 2)

    def testLengthOfSellList(self):
        """
        OrderBook must have the correct number of Sell orders
        """
        lst_sell = self.book.fetch_orders('S')
        self.assertEqual(len([s for s in lst_sell]), 4)

    def testOrderBookStdOutFormat(self):
        """
        OrderBook output to stdout needs to meet specifications
        """
        self.assertEqual(
            str(self.book),
            f"{os.linesep}     50,000     99 |    100         500{os.linesep}     25,500     98 |    100      10,000{os.linesep}                   |    103         100{os.linesep}                   |    105      20,000{os.linesep}")

    def testSaveAndReload(self):
        """
        OrderBook state restored from save file should be the same as the state
        before it was saved
        """
        self.book.save()
        loaded_book = load_book(TESTSAVEFILE)

        self.assertEqual(str(self.book), str(loaded_book))

    def testProcessBuyFullyFilledTrades(self):
        """
        OrderBook should process a Buy trade against open orders correctly
        """
        test_trades = os.path.join(TESTDIR, 'test2.txt')

        with open(test_trades, 'r') as f:
            data = [ln for ln in f.readlines()]

        self.book.process_orders(parse_data(data))

        self.assertEqual(
            str(self.book),
            f"{os.linesep}     50,000     99 |    105      14,600{os.linesep}     25,500     98 |                   {os.linesep}")

    def testProcessSellFullyFilledTrades(self):
        """
        Sell order at 98 fills the open Buy of 50,000 at 99 and partially fill
        the open Buy of 25,500 at 98
        """
        self.book.process_orders(parse_data(["10006,S,98,50500"]))

        self.assertEqual(
            str(self.book),
            f"{os.linesep}     25,000     98 |    100         500{os.linesep}                   |    100      10,000{os.linesep}                   |    103         100{os.linesep}                   |    105      20,000{os.linesep}")

    def testProcessBuyPartiallyFilledTrades(self):
        """
        Buy order at 100 fills 2 open Sell of 500 and 10,000 at 99
        Balance 500 of Buy order at 100 added to the top of the open Buy
        """
        self.book.process_orders(parse_data(["10006,B,100,11000"]))

        self.assertEqual(
            str(self.book),
            f"{os.linesep}        500    100 |    103         100{os.linesep}     50,000     99 |    105      20,000{os.linesep}     25,500     98 |                   {os.linesep}")

    def testProcessSellPartiallyFilledTrades(self):
        """
        Sell order at 99 fills the open Buy of 50,000 at 99
        Balance 10,000 of Sell order at 99 added to the top of the open Sell
        """
        self.book.process_orders(parse_data(["10006,S,99,60000"]))

        self.assertEqual(
            str(self.book),
            f"{os.linesep}     25,500     98 |     99      10,000{os.linesep}                   |    100         500{os.linesep}                   |    100      10,000{os.linesep}                   |    103         100{os.linesep}                   |    105      20,000{os.linesep}")

    def testProcessBuyUntilNoOpenSellTrades(self):
        """
        Fill all open Sell orders at the ask price
        """
        self.book.process_orders(parse_data(["10006,B,100,10500\n", "10007,B,103,100\n", "10008,B,105,20000"]))

        self.assertEqual(
            str(self.book),
            f"{os.linesep}     50,000     99 |                   {os.linesep}     25,500     98 |                   {os.linesep}")

    def testProcessSellUntilNoOpenBuyTrades(self):
        """
        Fill all open Buy orders at the bid price
        """
        self.book.process_orders(parse_data(["10006,S,99,50000\n", "10007,S,98,25500"]))

        self.assertEqual(
            str(self.book),
            f"{os.linesep}                   |    100         500{os.linesep}                   |    100      10,000{os.linesep}                   |    103         100{os.linesep}                   |    105      20,000{os.linesep}")

    def testMultipleExecutingOrders(self):
        """
        Execute a series of Orders
        """
        test_trades = os.path.join(TESTDIR, 'test3.txt')

        with open(test_trades, 'r') as f:
            data = [ln for ln in f.readlines()]

        self.book.process_orders(parse_data(data))

        self.assertEqual(
            str(self.book),
            f"{os.linesep}      5,000    104 |    105      14,600{os.linesep}     10,000    102 |                   {os.linesep}     50,000     99 |                   {os.linesep}     25,500     98 |                   {os.linesep}")

    def testEmptyOpenSellTradesAndRefill(self):
        """
        Fill all open Sell orders at the ask price
        """
        self.book.process_orders(parse_data(["10006,B,100,10500\n", "10007,B,103,100\n", "10008,B,105,20000\n", "10009,S,105,20000"]))

        self.assertEqual(
            str(self.book),
            f"{os.linesep}     50,000     99 |    105      20,000{os.linesep}     25,500     98 |                   {os.linesep}")

    def testEmptyOpenBuyTradesAndRefill(self):
        """
        Fill all open Buy orders at the bid price
        """
        self.book.process_orders(parse_data(["10006,S,99,50000\n", "10007,S,98,25500\n", "10008,B,97,50000"]))

        self.assertEqual(
            str(self.book),
            f"{os.linesep}     50,000     97 |    100         500{os.linesep}                   |    100      10,000{os.linesep}                   |    103         100{os.linesep}                   |    105      20,000{os.linesep}")


class TestOrderBookIcebergOrders(unittest.TestCase):
    def setUp(self) -> None:
        """
        Instantiate an OrderBook and process parsed input Buy/Sell data
        """
        test_filepath = os.path.join(TESTDIR, 'test_ice2.txt')

        with open(test_filepath, 'r') as f:
            data = [ln for ln in f.readlines()]
        
        self.book = OrderBook(TESTSAVEFILE)
        self.book.process_orders(parse_data(data))

    def testIcebergOrderBookStdOut(self):
        """
        Iceberg Buy order of 100,000 with a visible volume of 10,000 at 100
        """
        self.assertEqual(
            str(self.book),
            f"{os.linesep}     10,000    100 |    101      20,000{os.linesep}     50,000     99 |                   {os.linesep}     25,500     98 |                   {os.linesep}")