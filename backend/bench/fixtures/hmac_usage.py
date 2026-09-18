import hashlib
import hmac

token_weak = hmac.new(secret_key, message, hashlib.sha1)
token_ok = hmac.new(secret_key, message, hashlib.sha256)
