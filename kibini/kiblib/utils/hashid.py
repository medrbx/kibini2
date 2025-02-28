import hashlib

from kiblib.utils.conf import Config


def hash_identifier(identifier):
    salt = Config().get_config_salt()
    identifier = str(identifier)
    return hashlib.sha256(
        salt.encode() +
        identifier.encode()).hexdigest()[
        32:42]
