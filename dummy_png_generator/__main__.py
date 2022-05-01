from . import generate_dummy_png, METRICS_LIST


if __name__ == "__main__":
    """
    run module:
    >python -m dummy_png_generator
    """
    import sys
    import argparse
    import subprocess

    parser = argparse.ArgumentParser()
    parser.add_argument("size", action="store")
    parser.add_argument("units", action="store", choices=METRICS_LIST)
    parser.add_argument("--fastest", help="Use fastest way for generating", action="store_true", default=False)
    parser.add_argument("--open", help="Open image after generation", action="store_true", default=False)
    args = parser.parse_args()

    target_size = (int(args.size), args.units)

    image_path = generate_dummy_png(target_size, fastest=args.fastest)
    print(f"Image (~{target_size[0]} {target_size[1]})\nStored at: {image_path}")
    if args.open:
        open_image_command = \
            {
                'linux': 'xdg-open',
                'win32': 'explorer',
                'darwin': 'open'
            }[sys.platform]
        subprocess.run([open_image_command, image_path])

