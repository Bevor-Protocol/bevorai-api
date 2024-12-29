from tortoise import fields
from tortoise.models import Model


class Scan(Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()

    def __str__(self):
        return self.name
