from django import template
import hashlib

#create a registry object
register = template.Library()


#define a filter function and register it

@register.filter
def initials(full_name):
    """
    To return the first two initials of a full name in uppercase.
    """
    if not full_name:
        return ""

    words = full_name.split()
    if len(words)>=2:
        return (words[0][0] +words[1][0]).upper()
    else:
        return (words[0][0]).upper()

def brighten(hex_value):
    """
    Takes a hex value (00-ff) and scales it to a brighter range (120-255)
    """
    val = int(hex_value, 16)
    val = 71 + (val % 155)
    return f"{val:02x}"

@register.filter
def avatar_color(full_name):
    """
    Generates a color based on the user's full name.
    Returns a hex color string.
    """

    #default gray if no full name
    if not full_name:
        return "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"

    hash_object = hashlib.md5(full_name.encode())
    hex_digest = hash_object.hexdigest()

    color1 = f"#{brighten(hex_digest[0:2])}{brighten(hex_digest[2:4])}{brighten(hex_digest[4:6])}"
    color2 = f"#{brighten(hex_digest[6:8])}{brighten(hex_digest[8:10])}{brighten(hex_digest[10:12])}"

    return f"linear-gradient(135deg, {color1} 0%, {color2} 100%)"