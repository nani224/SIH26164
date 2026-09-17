import hashlib

digest_md5 = hashlib.md5(b"payload").hexdigest()
digest_sha1 = hashlib.sha1(b"payload").hexdigest()
digest_sha256 = hashlib.sha256(b"payload").hexdigest()
digest_via_new = hashlib.new("md5")
