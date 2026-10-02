def test_products_feed_requires_auth_and_returns_reaction_counts(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    listing = make_item(seller=seller)["item"]

    anonymous = client.get("/api/items")
    assert anonymous.status_code == 401

    response = client.get("/api/items", headers=buyer["headers"])

    assert response.status_code == 200, response.text
    product = next(item for item in response.json()["items"] if item["item_id"] == listing["item_id"])
    assert product["name"] == listing["name"]
    assert product["seller"]["username"] == seller["user"]["username"]
    assert product["like_count"] == 0
    assert product["comment_count"] == 0
    assert product["current_reaction"] is None
    assert product["my_order_status"] is None


def test_product_reaction_is_unique_and_removable(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    item_id = make_item(seller=seller)["item"]["item_id"]
    url = f"/api/items/{item_id}/reaction"

    liked = client.put(url, headers=buyer["headers"], json={"reaction_type": "LIKE"})
    repeated = client.put(url, headers=buyer["headers"], json={"reaction_type": "LIKE"})
    feed = client.get("/api/items", headers=buyer["headers"]).json()["items"]
    product = next(item for item in feed if item["item_id"] == item_id)

    assert liked.status_code == 200, liked.text
    assert repeated.status_code == 200, repeated.text
    assert product["like_count"] == 1
    assert product["dislike_count"] == 0
    assert product["current_reaction"] == "LIKE"

    disliked = client.put(url, headers=buyer["headers"], json={"reaction_type": "DISLIKE"})
    feed = client.get("/api/items", headers=buyer["headers"]).json()["items"]
    product = next(item for item in feed if item["item_id"] == item_id)
    assert disliked.status_code == 200, disliked.text
    assert product["like_count"] == 0
    assert product["dislike_count"] == 1
    assert product["current_reaction"] == "DISLIKE"

    removed = client.delete(url, headers=buyer["headers"])
    assert removed.status_code == 200, removed.text
    assert removed.json()["current_reaction"] is None
    assert removed.json()["like_count"] == 0
    assert removed.json()["dislike_count"] == 0


def test_product_comments_persist_with_author(client, make_user, make_item):
    seller = make_user(verified=True)
    buyer = make_user(verified=True)
    item_id = make_item(seller=seller)["item"]["item_id"]

    response = client.post(
        f"/api/items/{item_id}/comments",
        headers=buyer["headers"],
        json={"comment_text": "Can we meet near the library?"},
    )

    assert response.status_code == 201, response.text
    comments = client.get(f"/api/items/{item_id}/comments", headers=seller["headers"])
    assert comments.status_code == 200, comments.text
    comment = comments.json()["comments"][0]
    assert comment["comment_text"] == "Can we meet near the library?"
    assert comment["author"]["username"] == buyer["user"]["username"]


def test_authenticated_user_can_search_people_to_start_a_conversation(client, make_user):
    current_user = make_user(verified=True)
    first_match = make_user(verified=True)
    second_match = make_user(verified=True)

    anonymous = client.get("/api/users/search?q=student_")
    short_query = client.get("/api/users/search?q=x", headers=current_user["headers"])
    response = client.get("/api/users/search?q=student_", headers=current_user["headers"])

    assert anonymous.status_code == 401
    assert short_query.status_code == 422
    assert response.status_code == 200, response.text
    results = response.json()["users"]
    result_ids = {result["user_id"] for result in results}
    assert first_match["user"]["user_id"] in result_ids
    assert second_match["user"]["user_id"] in result_ids
    assert current_user["user"]["user_id"] not in result_ids
    assert all("email" not in result for result in results)


def test_messaging_sends_lists_and_marks_conversation_read(client, make_user):
    sender = make_user(verified=True)
    recipient = make_user(verified=True)

    sent = client.post(
        f"/api/messages/{recipient['user']['user_id']}",
        headers=sender["headers"],
        json={"message_text": "Is the textbook still available?"},
    )

    assert sent.status_code == 201, sent.text
    conversations = client.get("/api/messages/conversations", headers=recipient["headers"])
    assert conversations.status_code == 200, conversations.text
    conversation = conversations.json()["conversations"][0]
    assert conversation["user_id"] == sender["user"]["user_id"]
    assert conversation["unread_count"] == 1

    messages = client.get(
        f"/api/messages/{sender['user']['user_id']}",
        headers=recipient["headers"],
    )
    assert messages.status_code == 200, messages.text
    assert messages.json()["messages"][0]["message_text"] == "Is the textbook still available?"

    marked = client.post(
        f"/api/messages/{sender['user']['user_id']}/read",
        headers=recipient["headers"],
    )
    assert marked.status_code == 200, marked.text
    refreshed = client.get("/api/messages/conversations", headers=recipient["headers"])
    assert refreshed.json()["conversations"][0]["unread_count"] == 0


def test_deleting_message_hides_it_only_for_requesting_user(client, make_user):
    sender = make_user(verified=True)
    recipient = make_user(verified=True)
    sent = client.post(
        f"/api/messages/{recipient['user']['user_id']}",
        headers=sender["headers"],
        json={"message_text": "Can you still see this?"},
    )
    assert sent.status_code == 201, sent.text
    message_id = sent.json()["message"]["message_id"]

    deleted = client.delete(
        f"/api/messages/{sender['user']['user_id']}/{message_id}",
        headers=recipient["headers"],
    )

    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {"message_id": message_id, "hidden": True}
    recipient_messages = client.get(
        f"/api/messages/{sender['user']['user_id']}", headers=recipient["headers"]
    )
    sender_messages = client.get(
        f"/api/messages/{recipient['user']['user_id']}", headers=sender["headers"]
    )
    assert recipient_messages.json()["messages"] == []
    assert sender_messages.json()["messages"][0]["message_text"] == "Can you still see this?"


def test_chat_websocket_broadcasts_new_messages(client, make_user):
    sender = make_user(verified=True)
    recipient = make_user(verified=True)

    ticket = client.post("/api/ws/ticket", headers=recipient["headers"]).json()["ticket"]
    with client.websocket_connect(f"/api/ws/chat?ticket={ticket}") as websocket:
        response = client.post(
            f"/api/messages/{recipient['user']['user_id']}",
            headers=sender["headers"],
            json={"message_text": "Are you free to meet after class?"},
        )
        assert response.status_code == 201, response.text
        payload = websocket.receive_json()
        assert payload["type"] == "message"
        assert payload["message"]["message_text"] == "Are you free to meet after class?"
        assert payload["message"]["sender_id"] == sender["user"]["user_id"]


def test_messaging_rejects_self_and_anonymous_requests(client, make_user):
    user = make_user(verified=True)

    anonymous = client.get("/api/messages/conversations")
    self_message = client.post(
        f"/api/messages/{user['user']['user_id']}",
        headers=user["headers"],
        json={"message_text": "This should not be sent to myself."},
    )

    assert anonymous.status_code == 401
    assert self_message.status_code == 400
