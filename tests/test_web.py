import pytest

from app import config


# ---- Every page -------------------------------------------------------------
@pytest.mark.parametrize("path", ["/", "/orders/new", "/orders/ONW-DEMO01", "/ops/login"])
def test_every_page_shows_owner_lab_name_and_who_answered(browser, path):
    page = browser.get(path).get_data(as_text=True)
    assert config.OWNER_NAME in page
    assert config.LAB_NAME in page
    assert "Answered by" in page


def test_health_says_who_answered(browser):
    body = browser.get("/health").get_json()
    assert body["status"] == "ok" and body["answered_by"] and body["zone"]


# ---- Customer ---------------------------------------------------------------
def test_customer_places_an_order_and_lands_on_its_tracking_page(browser, valid_order):
    response = browser.post("/orders", valid_order)
    assert response.status_code == 302
    page = browser.get(response.headers["Location"]).get_data(as_text=True)
    assert "Order placed" in page
    assert "Esi Boateng" in page and "Tema" in page
    assert "USD 12.00" in page
    assert "Estimated delivery by" in page


def test_placed_order_appears_under_recent_orders(browser, valid_order):
    assert "Your recent orders" not in browser.get("/").get_data(as_text=True)
    code = browser.post("/orders", valid_order).headers["Location"].split("/")[-1].split("?")[0]
    home = browser.get("/").get_data(as_text=True)
    assert "Your recent orders" in home and code in home


def test_invalid_order_shows_error_and_keeps_what_was_typed(browser, valid_order):
    response = browser.post("/orders", {**valid_order, "recipient_name": ""})
    page = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "Please fill in: Recipient name" in page
    assert 'value="Kente Corner"' in page
    assert '<option value="tema" selected>' in page


def test_form_post_without_token_is_rejected(app, valid_order):
    assert app.test_client().post("/orders", data=valid_order).status_code == 400


def test_track_finds_an_order_whatever_the_case(browser):
    response = browser.get("/track?code=onw-demo01")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/orders/ONW-DEMO01")


def test_track_unknown_or_empty_code(browser):
    unknown = browser.get("/track?code=ONW-NOPE00")
    assert unknown.status_code == 404 and "could not find" in unknown.get_data(as_text=True)
    assert browser.get("/track?code=").status_code == 400
    assert browser.get("/orders/ONW-NOPE00").status_code == 404


def test_customer_cancels_before_pickup_but_not_after(browser):
    page = browser.get("/orders/ONW-DEMO02").get_data(as_text=True)
    assert "Cancel this order" in page
    assert browser.post("/orders/ONW-DEMO02/cancel").status_code == 302
    assert "Cancelled" in browser.get("/orders/ONW-DEMO02").get_data(as_text=True)

    assert "Cancel this order" not in browser.get("/orders/ONW-DEMO01").get_data(as_text=True)
    refused = browser.post("/orders/ONW-DEMO01/cancel")
    assert refused.status_code == 400 and "can no longer be cancelled" in refused.get_data(as_text=True)


def test_user_input_is_escaped(browser, valid_order):
    response = browser.post("/orders", {**valid_order, "sender_name": "<script>alert(1)</script>"})
    assert "<script>alert(1)</script>" not in browser.get(response.headers["Location"]).get_data(as_text=True)


# ---- Operations --------------------------------------------------------------
def test_operations_needs_the_passcode(browser):
    assert browser.get("/ops/").status_code == 302
    assert browser.post("/ops/orders/ONW-DEMO02/advance", token_from="/ops/login").status_code == 302
    assert browser.get("/api/orders/ONW-DEMO02").get_json()["status"] == "received"   # nothing changed

    wrong = browser.sign_in("guess")
    assert wrong.status_code == 401 and "not right" in wrong.get_data(as_text=True)
    assert browser.get("/ops/").status_code == 302


def test_staff_sign_in_see_dashboard_and_move_a_parcel(browser):
    assert browser.sign_in().status_code == 302
    dashboard = browser.get("/ops/").get_data(as_text=True)
    assert "In progress" in dashboard and "ONW-DEMO01" in dashboard and "ONW-DEMO02" in dashboard

    assert browser.post("/ops/orders/ONW-DEMO02/advance", token_from="/ops/").status_code == 302
    assert "Picked up" in browser.get("/orders/ONW-DEMO02").get_data(as_text=True)

    browser.post("/ops/orders/ONW-DEMO01/advance", token_from="/ops/")
    refused = browser.post("/ops/orders/ONW-DEMO01/advance", token_from="/ops/")
    assert refused.status_code == 400 and "already delivered" in refused.get_data(as_text=True)


def test_dashboard_search_and_filter(browser):
    browser.sign_in()
    by_text = browser.get("/ops/?q=kwame").get_data(as_text=True)
    assert "ONW-DEMO02" in by_text and "ONW-DEMO01" not in by_text
    by_status = browser.get("/ops/?status=out_for_delivery").get_data(as_text=True)
    assert "ONW-DEMO01" in by_status and "ONW-DEMO02" not in by_status
    assert "No orders match" in browser.get("/ops/?q=zzz").get_data(as_text=True)


def test_sign_out(browser):
    browser.sign_in()
    browser.post("/ops/logout", token_from="/ops/")
    assert browser.get("/ops/").status_code == 302


def test_sessions_work_across_servers_sharing_a_store(valid_order):
    """Two app instances on one store stand for two servers behind the load
    balancer: an order and a staff session from one are valid on the other."""
    from app import create_app
    from app.store import MemoryStore
    from tests.conftest import Browser

    store = MemoryStore(staff_passcode="shared")
    first, second = create_app(store), create_app(store)
    browser = Browser(first.test_client())
    browser.sign_in("shared")
    code = browser.post("/orders", valid_order).headers["Location"].split("/")[-1].split("?")[0]

    other = second.test_client()
    cookie = browser.client.get_cookie("session")
    other.set_cookie("session", cookie.value)
    assert other.get(f"/orders/{code}").status_code == 200
    assert other.get("/ops/").status_code == 200


# ---- API --------------------------------------------------------------------
def test_api_quote(browser):
    body = browser.get("/api/quote?pickup_city=accra&delivery_city=lagos&size=small&service=express").get_json()
    assert body["total_cents"] == 3000 and body["total"] == "USD 30.00"
    assert body["route_label"] == "Cross border" and body["eta"] == "within 2 days"
    assert browser.get("/api/quote?pickup_city=accra").status_code == 400


def test_api_place_and_fetch(app, valid_order):
    client = app.test_client()
    created = client.post("/api/orders", json=valid_order)
    assert created.status_code == 201
    body = created.get_json()
    assert body["status"] == "received" and body["price_cents"] == 1200
    assert client.get(f"/api/orders/{body['code']}").get_json() == body
    assert client.post("/api/orders", json={"sender_name": "Shop"}).status_code == 400
    assert client.get("/api/orders/ONW-NOPE00").status_code == 404
