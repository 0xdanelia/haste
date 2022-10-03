import sys

from display_handler import Display


# TODO: argparse the inputs properly
display = Display(sys.argv[1])
display.run_event_loop()
