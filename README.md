# pyperdeck
[![Documentation Status](https://readthedocs.org/projects/pyperdeck/badge/?version=latest)](https://pyperdeck.readthedocs.io/en/latest/?badge=latest) [![PyPI version](https://badge.fury.io/py/pyperdeck.svg)](https://badge.fury.io/py/pyperdeck)

![pyperdeck](https://user-images.githubusercontent.com/37907774/148882794-0019602c-269b-40dc-a38c-854f9e6ea37c.png)

Python interface for Blackmagic Design HyperDeck recorders.

## Installation
```
pip install pyperdeck
```

## Documentation
A full API reference and small walkthrough is available on [Read the Docs](http://pyperdeck.readthedocs.io/).

## Example
```python
from pyperdeck import Hyperdeck

deck = Hyperdeck('192.168.0.100')

deck.preview()
deck.record('my_recording')

# ... some time later

deck.stop()
deck.output()
deck.play()
```

## Additional Information
This is a work in progress and while it implements the vast majority of the HyperDeck Protocol, it does not do everything.  Questions, comments, and contributions are welcome.
