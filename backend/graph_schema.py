import graphene

from database import get_connection


class ItemType(graphene.ObjectType):
    item_id = graphene.Int()
    name = graphene.String()
    price = graphene.Float()
    category = graphene.String()
    status = graphene.String()


class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello from Campus X Mart GraphQL")
    item = graphene.Field(ItemType, item_id=graphene.Int(required=True))

    @staticmethod
    def resolve_item(root, info, item_id):
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SELECT item_id, name, price, category, status
                FROM items
                WHERE item_id = %s;
                """,
                (item_id,),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
            connection.close()

        if row is None:
            return None

        return {
            "item_id": row[0],
            "name": row[1],
            "price": float(row[2]),
            "category": row[3],
            "status": row[4],
        }


schema = graphene.Schema(query=Query)
