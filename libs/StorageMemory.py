class StorageMemory():
    def __init__(self):
        self.storage = {}

    def exists(self, key):
        if key in self.storage:
            return True
        return False

    def add(self, key, value):
        self.storage.setdefault(key, str(value))

    def update(self, key, value):
        self.storage[key] = str(value)

    def get(self, key):
        if key in self.storage:
            return self.storage[key]

    def delete(self, key):
        del self.storage[key]
