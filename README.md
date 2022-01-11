# pyperdeck
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