import redis


class StorageMemory():
    def __init__(self):
        self.storage = redis.StrictRedis(
            host='localhost',
            port=6379,
            decode_responses=True
        )

    def exists(self, key):
        if self.storage.exists(key):
            return True
        return False

    def add(self, key, value):
        self.storage.set(key, str(value))

    def update(self, key, value):
        self.storage.set(key, str(value))

    def get(self, key):
        return self.storage.get(key)

    def delete(self, key):
        self.storage.delete(key)
