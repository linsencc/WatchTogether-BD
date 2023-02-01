import random
import string


def get_random_string():
    result = ''.join(random.sample(string.ascii_letters + string.digits, 8))
    return result
