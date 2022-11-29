"""Generate dummy files with fixed size"""
from typing import Tuple, Literal, get_args
from PIL import Image, ImageFilter
from random import randint
import math
import os


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
METRICS = Literal["b", "kb", "mb", "gb"]
METRICS_LIST = get_args(METRICS)


def calculate_image_shape(target_size: int, color_depth: int = 32) -> Tuple[int, int]:
    """
    Calculate image shape(x, y) depend on target size

    :param target_size: Target size of image file(in bytes)
    :param color_depth: Color pallet of image
    :return: (x, y) size
    """
    #target_size = x*y * color_depth / 8
    #TODO: add calculation of image chunks size
    x_y = math.floor(math.sqrt(target_size / color_depth * 8))
    return x_y, x_y


def modify_image(image: Image.Image) -> Image.Image:
    """
    Modify pixels on image

    :param image: Input image
    :return: Modified image
    """
    data = image.load()
    img_size = image.size

    seed = randint(3, 7)

    color_per_pixel_x = 256/img_size[0]
    color_per_pixel_y = 256/img_size[1]

    def _func(x: int, y: int):
        return int(((color_per_pixel_x*x) ** 2 - (color_per_pixel_y*y) ** 2) % 200)

    def _gradient(x: int, y: int):
        return int((x*color_per_pixel_x+y*color_per_pixel_y)/2)

    for x in range(img_size[0]):
        for y in range(img_size[1]):
            data[x, y] = (
                         255-_func(x, y)+20*seed,
                         _gradient(x, y),
                         255-_gradient(x, y)+10*seed,
                         255
                     )

    return image.filter(ImageFilter.GaussianBlur(0.7))


def generate_image(target_size: int, fastest: bool = False) -> Image.Image:
    """
    Generate image with specific size

    :param target_size: Target size of file in bytes
    :param fastest: Use fastest way(skip image, modifying)
    :return: Generated image
    """
    size = calculate_image_shape(target_size)
    image = Image.new('RGBA', size, (134, 219, 142, 255))
    return image if fastest else modify_image(image)


def generate_dummy_png(target_size: Tuple[int, METRICS] = (1024, "mb"),
                       fastest: bool = False,
                       dummy_prefix: str = "dummy_png",
                       dest_dir: str = MODULE_DIR
                       ) -> str:
    """
    Generate image with specific size

    :param dest_dir: Generated files will be stored in this dir
    :param target_size: Target size of file in bytes
    :param fastest: Use fastest way(skip image modifying)
    :param dummy_prefix: Generated file prefix
    :return: Path to generated dummy file
    """
    size, metric = round(target_size[0]), target_size[1]

    multiplier = METRICS_LIST.index(metric) if metric in METRICS_LIST else 2
    dummy_size_in_bytes = size*(1024**multiplier)
    dummy_file_name = f"{dummy_prefix}_{size}_{METRICS_LIST[multiplier]}.png"

    image = generate_image(dummy_size_in_bytes, fastest=fastest)
    image_path = os.path.join(dest_dir, dummy_file_name)

    image.save(image_path, compress_level=0, optimize=False)
    return image_path
