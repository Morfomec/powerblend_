import os

#this is to build path for images in products
def product_image_upload_path(instance, filename):
    return os.path.join("products", instance.product.slug, filename)