from mnu_gui import MNUploaderGUI
from config import MNUClientConfig


if __name__ == "__main__":
    import argparse
    arguments = argparse.ArgumentParser()
    arguments.add_argument("--server-addr", help="MNU server address", default=MNUClientConfig().server_addr)
    arguments.add_argument("--server-port", help="MNU server port", default=MNUClientConfig().server_port)
    arguments.add_argument("--auto-connect", help="Try to auto connect to server", action="store_true", default=MNUClientConfig().auto_connect)
    args = arguments.parse_args()
    MNUploaderGUI(args.server_addr, args.server_port, args.auto_connect).run()
