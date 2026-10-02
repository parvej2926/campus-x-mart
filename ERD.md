# Campus X Mart ERD

## Core entities

- Users
  - user_id
  - username
  - full_name
  - email
  - phone
  - password_hash
  - role
  - verification flags

- Items
  - item_id
  - seller_id
  - category
  - name
  - description
  - price
  - condition
  - available_from
  - status

- Item media
  - media_id
  - item_id
  - media_type
  - storage_provider
  - media_url

- Messages
  - message_id
  - sender_id
  - receiver_id
  - message_text
  - sent_at

- Reviews
  - review_id
  - item_id
  - user_id
  - rating
  - review_text

- Orders
  - order_id
  - item_id
  - buyer_id
  - seller_id
  - agreed_price
  - status

## Relationships

- Users to Items: one-to-many
- Users to Messages: one-to-many as sender and receiver
- Items to Item Media: one-to-many
- Items to Reviews: one-to-many
- Items to Orders: one-to-many
- Items to Comments: one-to-many
- Users to Notifications: one-to-many

## Notes

This ERD reflects the live database schema already implemented in the PostgreSQL schema file. It is a project documentation artifact for assignment reporting, while the schema.sql file remains the canonical database definition.
