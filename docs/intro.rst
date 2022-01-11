Introduction
============

Installation
------------

This package is available on  ``pip``::

    pip install pyperdeck

Requirements
------------
Pyperdeck was developed with Python 3.9 but contains no external dependencies so should be compatiable with all current versions of Python 3.7+.

The HyperDeck you're using should be fully updated, this library was developed on a `HyperDeck Studio HD Plus <https://www.blackmagicdesign.com/products/hyperdeckstudio/techspecs/W-HYD-12>`_ but should be compatiable with all recent HyperDeck models with an ethernet connection.

Getting Started
----------------
The following code example shows how to initiate a connection with a HyperDeck::
    
    from pyperdeck import Hyperdeck

    deck = Hyperdeck('192.168.0.100')

=================
Recording
=================
The HyperDeck has two modes: "preview" and "output".  Preview mode acts as a direct pass through of the input signal to the output signal and allows for recording.
Output mode is for playing back previously recorded clips and overrides the output signal with media from it's internal storage::

    # Put the HyperDeck in `Preview Mode`:
    deck.preview()

There are two ways to record, one allows you to set a custom file name, and the other uses a generic file name with an incremental counter::

    # Record a file named `my_recording.mov`:
    deck.record('my_recording')

    # Record a file with a generic file name:
    deck.record()

    # ... some time later, stop the recording:
    deck.stop()

.. note:: The HyperDeck will always append the correct file extension for the current settings, so calling ``deck.record('my_recording.mov')`` could result in a file called `my_recording.mov.mov` or `my_recording.mov.mp4`.

=================
Playback
=================
In order to playback clips, the HyperDeck must be in output mode::

    deck.output()

The HyperDeck uses an internal timeline to playback recordings.  Each recording is automatically added to the end of the timeline.
When entering output mode, the timeline's playhead is automatically placed at the beginning of the most recently recorded clip::

    # Loop over just the last recorded clip:
    deck.play(loop=True, single_clip=True)

    # Play the entire timeline:
    deck.go_within_timeline(1) # move playhead to the beginning
    deck.play()

    # Play in slow motion:
    deck.play(25) # playback at 25% speed