# Kevin Stilt Assessment [WIP]

### How to run

 1. Create virtual environment using python 3.7 and above `python3 -m venv venv`
 2. Run `pip install -r requirements.txt`. This step is optional the current package it only use for the formatting using `pre-commit`.
 3. Run `cat dispatch_orders.json|python order.py` . It takes arguments for the strategy. `cat dispatch_orders.json|python order.py -s matched`. It has two options `fifo` and `matched`.

 For sample result you could see on the log file for fifo and matched strategy.

