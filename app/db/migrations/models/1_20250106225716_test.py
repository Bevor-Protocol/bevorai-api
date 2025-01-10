from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE auth add column "test" varchar(14);
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER table auth drop column "test";
        """
