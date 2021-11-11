# Single Security OrderBook
Simple, lightweight application that maintains an order book of buy and sell trades on a single ticker.Implemented as the central limit order book where orders are matched using 'price time priority'

The application accepts orders through the standard in. All matched orders are printed to the standard out as the execution is confirmed. Finally, the final state of the orderbook is also printed before the application exits.

The application also maintains a saved state of all open orders resulting from the previous round of processing. When it is called the second time to process a new stream of orders, execution will resume from the existing state of the order book. To start from a clean state, do clear the saved files inside `saved/`

## Requirements
* python >= 3.8
* pip

### External python modules
* pyinstaller _(Optional)_ <br>Only used for compiling an executable binary of the application

## Installation
**Note** It is strongly encouraged to perform the installation through a python virtual environment or a container. The Makefile included with the application assumes that you already have your virtual environment activated.<br>

1. Install all depdencies. Optionally, run the unittests to ensure everything is set up fine.<br>
`$ make prepare` <br>
`$ make test`

2. Install the OrderBook binary. The binary is automatically moved from `dist/` to the root folder<br>
`$ make install`

## Usage
The application package includes test files that can be used as sample input to the OrderBook. These are located inside the `tests` folder.

1. Populate the order book <br>
`./exchange < tests/test1.txt`
```

     50,000     99 |    100         500
     25,500     98 |    100      10,000
                   |    103         100
                   |    105      20,000

```

2. Fill some of the open sell orders <br>
`./exchange < tests/test2.txt`
```

trade 10006,10001,100,500
trade 10006,10002,100,10000
trade 10006,10004,103,100
trade 10006,10005,105,5400
     50,000     99 |    105      14,600
     25,500     98 |

```

3. From a clean state. Load the sample file with an iceberg trade <br>
`./exchange < tests/test_ice2.txt`
```

trade ice1,10002,100,10000
trade ice1,10001,100,7500
     10,000    100 |    101      20,000
     50,000     99 |
     25,500     98 |

```