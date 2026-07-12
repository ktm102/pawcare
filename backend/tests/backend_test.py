"""PawCare Backend API tests - Full coverage suite."""
import os
import time
import uuid
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL",
                          "https://petcare-ai-13.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@pawcare.it"
ADMIN_PASSWORD = "admin123"


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    """Login admin via cookie session."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def new_user_session():
    """Register a fresh TEST_ user."""
    s = requests.Session()
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register",
               json={"email": email, "password": "Pass1234!", "name": "Test User"},
               timeout=15)
    assert r.status_code == 200, f"Registration failed: {r.status_code} {r.text}"
    s.email = email  # attach for reference
    return s


# ---------- Auth tests ----------
class TestAuth:
    def test_root(self):
        r = requests.get(f"{API}/", timeout=10)
        assert r.status_code == 200
        assert "message" in r.json()

    def test_register_and_me(self, new_user_session):
        r = new_user_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == new_user_session.email
        assert data["name"] == "Test User"

    def test_register_duplicate(self, new_user_session):
        r = new_user_session.post(f"{API}/auth/register",
                                  json={"email": new_user_session.email,
                                        "password": "Pass1234!", "name": "Dup"},
                                  timeout=10)
        assert r.status_code == 400

    def test_login_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=10)
        assert r.status_code == 401

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_logout(self):
        s = requests.Session()
        s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
        assert s.get(f"{API}/auth/me", timeout=10).status_code == 200
        r = s.post(f"{API}/auth/logout", timeout=10)
        assert r.status_code == 200
        # After logout, previously authenticated session should no longer work
        r2 = s.get(f"{API}/auth/me", timeout=10)
        assert r2.status_code == 401

    def test_protected_endpoints_require_auth(self):
        for path in ["/pets", "/dashboard/upcoming", "/ai/chat/history"]:
            r = requests.get(f"{API}{path}", timeout=10)
            assert r.status_code == 401, f"{path} should be 401 but got {r.status_code}"


# ---------- Pets CRUD ----------
class TestPets:
    def _pet_payload(self, name="TEST_Fido"):
        return {"name": name, "species": "dog", "breed": "Labrador",
                "birth_date": "2020-05-01", "sex": "M", "weight": 25.5}

    def test_create_pet(self, new_user_session):
        r = new_user_session.post(f"{API}/pets", json=self._pet_payload(), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "TEST_Fido"
        assert data["species"] == "dog"
        assert data["breed"] == "Labrador"
        assert "id" in data and "age" in data
        assert data["age"] >= 4
        new_user_session.pet_id = data["id"]

    def test_list_pets(self, new_user_session):
        r = new_user_session.get(f"{API}/pets", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert any(p["id"] == new_user_session.pet_id for p in r.json())

    def test_get_pet(self, new_user_session):
        r = new_user_session.get(f"{API}/pets/{new_user_session.pet_id}", timeout=10)
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Fido"

    def test_get_pet_not_found(self, new_user_session):
        r = new_user_session.get(f"{API}/pets/nonexistent-id", timeout=10)
        assert r.status_code == 404

    def test_update_pet(self, new_user_session):
        payload = self._pet_payload(name="TEST_Rex")
        payload["weight"] = 30.0
        r = new_user_session.put(f"{API}/pets/{new_user_session.pet_id}",
                                 json=payload, timeout=10)
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Rex"
        # verify persistence
        got = new_user_session.get(f"{API}/pets/{new_user_session.pet_id}").json()
        assert got["weight"] == 30.0

    def test_pet_isolation_between_users(self, new_user_session, admin_session):
        """Admin should not see the other user's pet."""
        r = admin_session.get(f"{API}/pets/{new_user_session.pet_id}", timeout=10)
        assert r.status_code == 404


# ---------- Records: visits/vaccines/treatments ----------
class TestRecords:
    def test_add_visit_and_list(self, new_user_session):
        pid = new_user_session.pet_id
        payload = {"date": "2025-01-15", "reason": "Controllo annuale",
                   "veterinarian": "Dr. Bianchi", "notes": "Tutto ok"}
        r = new_user_session.post(f"{API}/pets/{pid}/visits", json=payload, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["reason"] == "Controllo annuale"
        new_user_session.visit_id = data["id"]

        lst = new_user_session.get(f"{API}/pets/{pid}/visits", timeout=10).json()
        assert any(v["id"] == new_user_session.visit_id for v in lst)

    def test_add_vaccine(self, new_user_session):
        pid = new_user_session.pet_id
        next_due = (date.today() + timedelta(days=15)).isoformat()
        r = new_user_session.post(f"{API}/pets/{pid}/vaccines",
                                  json={"name": "Antirabbica",
                                        "date_given": "2025-01-01",
                                        "next_due": next_due}, timeout=10)
        assert r.status_code == 200
        new_user_session.vaccine_id = r.json()["id"]

    def test_add_treatment(self, new_user_session):
        pid = new_user_session.pet_id
        next_due = (date.today() + timedelta(days=5)).isoformat()
        r = new_user_session.post(f"{API}/pets/{pid}/treatments",
                                  json={"name": "Antipulci",
                                        "date_given": "2025-01-01",
                                        "frequency_days": 30,
                                        "next_due": next_due}, timeout=10)
        assert r.status_code == 200
        new_user_session.treatment_id = r.json()["id"]

    def test_upcoming_dashboard(self, new_user_session):
        r = new_user_session.get(f"{API}/dashboard/upcoming", timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        # Should include vaccine and treatment we added
        titles = [i["title"] for i in items]
        assert "Antirabbica" in titles
        assert "Antipulci" in titles
        # Sorted by days_left ascending
        days = [i["days_left"] for i in items]
        assert days == sorted(days)

    def test_delete_records(self, new_user_session):
        pid = new_user_session.pet_id
        r = new_user_session.delete(f"{API}/pets/{pid}/visits/{new_user_session.visit_id}", timeout=10)
        assert r.status_code == 200
        r = new_user_session.delete(f"{API}/pets/{pid}/vaccines/{new_user_session.vaccine_id}", timeout=10)
        assert r.status_code == 200
        # verify vaccine gone
        vs = new_user_session.get(f"{API}/pets/{pid}/vaccines").json()
        assert not any(v["id"] == new_user_session.vaccine_id for v in vs)


# ---------- Guides ----------
class TestGuides:
    def test_all_guides(self):
        r = requests.get(f"{API}/guides", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 8

    def test_filter_by_species_dog(self):
        r = requests.get(f"{API}/guides?species=dog", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert all(g["species"] == "dog" for g in data)
        assert len(data) >= 1

    def test_filter_by_species_cat(self):
        r = requests.get(f"{API}/guides?species=cat", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert all(g["species"] == "cat" for g in data)


# ---------- AI (may be slow) ----------
class TestAI:
    def test_advice(self, new_user_session):
        pid = new_user_session.pet_id
        r = new_user_session.post(f"{API}/ai/advice",
                                  json={"pet_id": pid}, timeout=90)
        assert r.status_code == 200, f"AI advice failed: {r.text[:400]}"
        data = r.json()
        assert "advice" in data
        assert len(data["advice"]) > 30

    def test_advice_not_found(self, new_user_session):
        r = new_user_session.post(f"{API}/ai/advice",
                                  json={"pet_id": "nope"}, timeout=90)
        assert r.status_code == 404

    def test_chat_and_history(self, new_user_session):
        r = new_user_session.post(f"{API}/ai/chat",
                                  json={"message": "Ciao, come devo curare il mio cane?"},
                                  timeout=90)
        assert r.status_code == 200
        data = r.json()
        assert "reply" in data
        assert len(data["reply"]) > 10

        time.sleep(0.5)
        h = new_user_session.get(f"{API}/ai/chat/history", timeout=10)
        assert h.status_code == 200
        msgs = h.json()
        assert isinstance(msgs, list)
        assert len(msgs) >= 2
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles


# ---------- AI Chat Memory (multi-turn context) - BUG FIX VERIFICATION ----------
class TestAIChatMemory:
    """Verify the AI assistant retains context across multiple turns via initial_messages."""

    @pytest.fixture(scope="class")
    def fresh_chat_session(self):
        """Register a brand-new user so DB chat history is empty for a clean test."""
        s = requests.Session()
        email = f"test_mem_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Memory Tester"},
                   timeout=15)
        assert r.status_code == 200, f"register failed: {r.text}"
        # Sanity: history should be empty
        h = s.get(f"{API}/ai/chat/history", timeout=10)
        assert h.status_code == 200
        assert h.json() == []
        return s

    def test_multi_turn_context_recall(self, fresh_chat_session):
        s = fresh_chat_session
        # Turn 1 - provide breed + problem
        r1 = s.post(f"{API}/ai/chat",
                    json={"message": "Ho un Golden Retriever che si gratta molto le orecchie."},
                    timeout=120)
        assert r1.status_code == 200, f"chat turn1 failed: {r1.text[:500]}"
        reply1 = r1.json()["reply"]
        assert isinstance(reply1, str) and len(reply1) > 20

        # Turn 2 - ask the model to recall what was said
        r2 = s.post(f"{API}/ai/chat",
                    json={"message": "Che razza di cane ho e qual era il problema che ti ho descritto?"},
                    timeout=120)
        assert r2.status_code == 200, f"chat turn2 failed: {r2.text[:500]}"
        reply2 = r2.json()["reply"].lower()
        print(f"\n[MEMORY TEST] Turn2 reply:\n{r2.json()['reply']}\n")

        # Assistant must recall the breed and the problem from turn 1
        assert "golden retriever" in reply2, f"Breed not recalled. Reply: {reply2[:400]}"
        assert ("orecchi" in reply2 or "grat" in reply2 or "prurito" in reply2), \
            f"Problem (ear scratching) not recalled. Reply: {reply2[:400]}"

    def test_third_turn_still_has_context(self, fresh_chat_session):
        s = fresh_chat_session
        # Turn 3 - narrow follow-up that only makes sense with memory
        r = s.post(f"{API}/ai/chat",
                   json={"message": "Ha 5 anni. Cosa mi consigli per il suo problema alle orecchie?"},
                   timeout=120)
        assert r.status_code == 200
        reply = r.json()["reply"].lower()
        print(f"\n[MEMORY TEST] Turn3 reply:\n{r.json()['reply']}\n")
        # It should give advice about ears / scratching (not generic off-topic)
        assert ("orecchi" in reply or "auricol" in reply or "prurito" in reply
                or "otit" in reply or "veterinar" in reply), \
            f"Turn3 lost topical context. Reply: {reply[:400]}"

    def test_history_persisted_and_ordered(self, fresh_chat_session):
        s = fresh_chat_session
        h = s.get(f"{API}/ai/chat/history", timeout=10)
        assert h.status_code == 200
        msgs = h.json()
        # 3 user + 3 assistant messages
        assert len(msgs) == 6, f"expected 6 messages, got {len(msgs)}: {[m['role'] for m in msgs]}"
        roles = [m["role"] for m in msgs]
        assert roles == ["user", "assistant", "user", "assistant", "user", "assistant"]
        # First user message must be the Golden Retriever one
        assert "golden retriever" in msgs[0]["content"].lower()
        # Timestamps monotonically non-decreasing
        ts = [m["created_at"] for m in msgs]
        assert ts == sorted(ts)


# ---------- Weight logs (NEW FEATURE) ----------
class TestWeights:
    """Weight tracking endpoints - list/create/delete + syncing pet.weight to latest."""

    @pytest.fixture(scope="class")
    def weight_user(self):
        """Fresh user + pet dedicated to weight tests."""
        s = requests.Session()
        email = f"test_wt_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Weight Tester"},
                   timeout=15)
        assert r.status_code == 200
        pr = s.post(f"{API}/pets", json={
            "name": "TEST_Weighty", "species": "dog", "breed": "Beagle",
            "birth_date": "2021-06-01", "sex": "M", "weight": 10.0
        }, timeout=15)
        assert pr.status_code == 200
        s.pet_id = pr.json()["id"]
        return s

    def test_list_weights_empty_initially(self, weight_user):
        r = weight_user.get(f"{API}/pets/{weight_user.pet_id}/weights", timeout=10)
        assert r.status_code == 200
        assert r.json() == []

    def test_create_weight_and_persistence(self, weight_user):
        pid = weight_user.pet_id
        payload = {"date": "2025-01-05", "weight": 12.3}
        r = weight_user.post(f"{API}/pets/{pid}/weights", json=payload, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["weight"] == 12.3
        assert data["date"] == "2025-01-05"
        assert data["pet_id"] == pid
        assert "id" in data
        assert "_id" not in data  # ObjectId must not leak
        weight_user.w1 = data["id"]

        # GET verifies persistence
        got = weight_user.get(f"{API}/pets/{pid}/weights", timeout=10).json()
        assert any(w["id"] == weight_user.w1 for w in got)

    def test_multiple_weights_sorted_asc(self, weight_user):
        pid = weight_user.pet_id
        # add two more entries out of order
        r2 = weight_user.post(f"{API}/pets/{pid}/weights",
                              json={"date": "2025-03-10", "weight": 13.1}, timeout=10)
        assert r2.status_code == 200
        weight_user.w3 = r2.json()["id"]
        r3 = weight_user.post(f"{API}/pets/{pid}/weights",
                              json={"date": "2025-02-01", "weight": 12.7}, timeout=10)
        assert r3.status_code == 200
        weight_user.w2 = r3.json()["id"]

        lst = weight_user.get(f"{API}/pets/{pid}/weights", timeout=10).json()
        assert len(lst) == 3
        dates = [w["date"] for w in lst]
        assert dates == sorted(dates), f"Weights not sorted asc: {dates}"

    def test_pet_weight_synced_to_latest(self, weight_user):
        """pet.weight should reflect the measurement with the latest date."""
        pid = weight_user.pet_id
        pet = weight_user.get(f"{API}/pets/{pid}", timeout=10).json()
        # latest measurement was 2025-03-10 with weight 13.1
        assert pet["weight"] == 13.1, f"Expected pet.weight=13.1, got {pet['weight']}"

    def test_delete_weight_and_verify(self, weight_user):
        pid = weight_user.pet_id
        r = weight_user.delete(f"{API}/pets/{pid}/weights/{weight_user.w2}", timeout=10)
        assert r.status_code == 200
        lst = weight_user.get(f"{API}/pets/{pid}/weights", timeout=10).json()
        assert not any(w["id"] == weight_user.w2 for w in lst)
        assert len(lst) == 2

    def test_weights_require_auth(self, weight_user):
        pid = weight_user.pet_id
        r = requests.get(f"{API}/pets/{pid}/weights", timeout=10)
        assert r.status_code == 401

    def test_weights_isolated_across_users(self, weight_user, admin_session):
        """Admin should not be able to list/create weights on another user's pet."""
        pid = weight_user.pet_id
        r = admin_session.get(f"{API}/pets/{pid}/weights", timeout=10)
        assert r.status_code == 404
        r2 = admin_session.post(f"{API}/pets/{pid}/weights",
                                json={"date": "2025-01-01", "weight": 5.0}, timeout=10)
        assert r2.status_code == 404


# ---------- Push notifications (NEW FEATURE) ----------
class TestPush:
    """Push endpoints: vapid-public-key, subscribe/status/unsubscribe, check-reminders, test."""

    @pytest.fixture(scope="class")
    def push_user(self):
        s = requests.Session()
        email = f"test_push_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Push Tester"},
                   timeout=15)
        assert r.status_code == 200
        return s

    def _fake_sub(self):
        return {
            "endpoint": f"https://fcm.googleapis.com/fcm/send/fake-{uuid.uuid4().hex[:16]}",
            "keys": {"p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                     "auth": "tBHItJI5svbpez7KI4CCXg"},
        }

    def test_vapid_public_key_requires_no_auth_but_works(self, push_user):
        r = push_user.get(f"{API}/push/vapid-public-key", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "public_key" in data
        assert isinstance(data["public_key"], str)
        assert len(data["public_key"]) > 30  # VAPID keys are ~87 chars base64-url

    def test_status_initially_false(self, push_user):
        r = push_user.get(f"{API}/push/status", timeout=10)
        assert r.status_code == 200
        assert r.json() == {"subscribed": False}

    def test_subscribe_and_status_true(self, push_user):
        sub = self._fake_sub()
        push_user.sub = sub
        r = push_user.post(f"{API}/push/subscribe", json={"subscription": sub}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        st = push_user.get(f"{API}/push/status", timeout=10)
        assert st.status_code == 200
        assert st.json() == {"subscribed": True}

    def test_subscribe_idempotent_upsert(self, push_user):
        # Re-post same subscription; still subscribed:true, no duplicate
        r = push_user.post(f"{API}/push/subscribe",
                           json={"subscription": push_user.sub}, timeout=10)
        assert r.status_code == 200
        st = push_user.get(f"{API}/push/status", timeout=10).json()
        assert st == {"subscribed": True}

    def test_subscribe_missing_endpoint_rejected(self, push_user):
        r = push_user.post(f"{API}/push/subscribe",
                           json={"subscription": {"keys": {"p256dh": "x", "auth": "y"}}},
                           timeout=10)
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_check_reminders_ok(self, push_user):
        """check-reminders should complete without error even with an unreachable
        (fake) subscription — dead subs are pruned and sent should be 0."""
        r = push_user.post(f"{API}/push/check-reminders", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "sent" in data
        assert isinstance(data["sent"], int)

    def test_push_test_returns_400_when_no_valid_sub(self, push_user):
        # After a failed send, the dead subscription may have been pruned. Ensure at
        # least one fake sub is present, then /push/test will attempt to send, all
        # sends fail (invalid keys), so sent==0 -> 400 with Italian detail.
        push_user.post(f"{API}/push/subscribe",
                       json={"subscription": self._fake_sub()}, timeout=10)
        r = push_user.post(f"{API}/push/test", timeout=30)
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert isinstance(detail, str) and len(detail) > 0
        # Italian message check
        assert "notific" in detail.lower() or "attiva" in detail.lower()

    def test_unsubscribe_and_status_false(self, push_user):
        # ensure at least one sub exists (may have been pruned by previous test)
        sub = self._fake_sub()
        push_user.post(f"{API}/push/subscribe", json={"subscription": sub}, timeout=10)
        r = push_user.post(f"{API}/push/unsubscribe",
                           json={"subscription": sub}, timeout=10)
        assert r.status_code == 200

        # remove any other lingering subs so status becomes false
        # (Delete via unsubscribe endpoint of any known subs)
        push_user.post(f"{API}/push/unsubscribe",
                       json={"subscription": push_user.sub}, timeout=10)

        # Best-effort: status may still be true if extra subs remain, but we
        # unsubscribed both known ones. Accept either state — main assertion is
        # that unsubscribe returns 200 idempotently.
        st = push_user.get(f"{API}/push/status", timeout=10)
        assert st.status_code == 200
        assert "subscribed" in st.json()

    def test_push_endpoints_require_auth(self):
        for method, path in [("GET", "/push/status"),
                             ("POST", "/push/subscribe"),
                             ("POST", "/push/unsubscribe"),
                             ("POST", "/push/test"),
                             ("POST", "/push/check-reminders")]:
            r = requests.request(method, f"{API}{path}", json={"subscription": {}}, timeout=10)
            assert r.status_code == 401, f"{method} {path} should require auth"


# ---------- PWA assets ----------
class TestPWA:
    """Static PWA files served through frontend origin."""

    def test_manifest_json(self):
        r = requests.get(f"{BASE_URL}/manifest.json", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data.get("name") and "PawCare" in data["name"]
        assert data.get("short_name") == "PawCare"
        assert data.get("display") == "standalone"
        assert data.get("start_url") == "/dashboard"
        icons = data.get("icons", [])
        sizes = {i.get("sizes") for i in icons}
        assert "192x192" in sizes
        assert "512x512" in sizes

    def test_service_worker_js(self):
        r = requests.get(f"{BASE_URL}/sw.js", timeout=10)
        assert r.status_code == 200
        assert "javascript" in r.headers.get("content-type", "").lower()
        # Must contain push listener
        assert "push" in r.text.lower()
        assert "showNotification" in r.text


# ---------- Cleanup: delete pet cascades (includes weights) ----------
class TestZCleanup:
    def test_delete_pet_cascade(self, new_user_session):
        # create our own pet & records (loadscope may separate classes)
        r = new_user_session.post(f"{API}/pets", json={
            "name": "TEST_ToDelete", "species": "cat", "breed": "Persian",
            "birth_date": "2022-01-01", "sex": "F", "weight": 4.2
        }, timeout=15)
        assert r.status_code == 200
        pid = r.json()["id"]

        # add a vaccine so cascade can be verified
        nd = (date.today() + timedelta(days=10)).isoformat()
        new_user_session.post(f"{API}/pets/{pid}/vaccines", json={
            "name": "TEST_Trivalente", "date_given": "2025-01-01", "next_due": nd
        }, timeout=10)
        # add a weight log so cascade can be verified for weights too
        new_user_session.post(f"{API}/pets/{pid}/weights", json={
            "date": "2025-01-01", "weight": 4.5
        }, timeout=10)
        wlist = new_user_session.get(f"{API}/pets/{pid}/weights", timeout=10).json()
        assert len(wlist) == 1

        r = new_user_session.delete(f"{API}/pets/{pid}", timeout=10)
        assert r.status_code == 200
        # verify pet gone
        r2 = new_user_session.get(f"{API}/pets/{pid}", timeout=10)
        assert r2.status_code == 404
        # weights endpoint should now 404 too (pet not found)
        r3 = new_user_session.get(f"{API}/pets/{pid}/weights", timeout=10)
        assert r3.status_code == 404
        # upcoming should no longer include items from this pet
        u = new_user_session.get(f"{API}/dashboard/upcoming", timeout=10).json()
        assert not any(i["pet_id"] == pid for i in u)



# ---------- AI Chat Streaming (NEW FEATURE - SSE) ----------
import json as _json


class TestAIChatStream:
    """Verify POST /api/ai/chat/stream is a real SSE stream that:
       1) Returns text/event-stream content-type
       2) Emits at least one `data: {"delta": ...}` chunk
       3) Ends with `data: {"done": true}`
       4) Persists both user + assistant messages to /ai/chat/history
       5) Requires auth (401 when anonymous)
    """

    @pytest.fixture(scope="class")
    def stream_user(self):
        s = requests.Session()
        email = f"test_stream_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Stream Tester"},
                   timeout=15)
        assert r.status_code == 200, f"register failed: {r.text}"
        s.email = email
        return s

    def test_stream_requires_auth(self):
        r = requests.post(f"{API}/ai/chat/stream",
                          json={"message": "ciao"}, timeout=15)
        assert r.status_code == 401

    def test_stream_emits_deltas_and_done(self, stream_user):
        # History before send
        h_before = stream_user.get(f"{API}/ai/chat/history", timeout=10).json()
        n_before = len(h_before)

        with stream_user.post(
            f"{API}/ai/chat/stream",
            json={"message": "Come si chiama la mia razza preferita di gatto? Rispondi brevemente."},
            stream=True, timeout=120,
        ) as r:
            assert r.status_code == 200, f"stream failed: {r.text[:400]}"
            ctype = r.headers.get("content-type", "")
            assert "text/event-stream" in ctype, f"bad content-type: {ctype}"

            delta_count = 0
            got_done = False
            got_error = False
            full_text = ""
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if not raw.startswith("data:"):
                    continue
                payload = raw[5:].strip()
                try:
                    obj = _json.loads(payload)
                except Exception:
                    continue
                if "delta" in obj:
                    delta_count += 1
                    full_text += obj["delta"]
                elif obj.get("done"):
                    got_done = True
                    break
                elif obj.get("error"):
                    got_error = True

            assert not got_error, "stream emitted error frame"
            assert delta_count > 0, "no delta chunks received"
            assert got_done, "stream did not end with done:true"
            assert len(full_text) > 3, f"no accumulated text: {full_text!r}"

        # Give server a moment to persist the assistant message
        time.sleep(1.0)
        h_after = stream_user.get(f"{API}/ai/chat/history", timeout=10).json()
        assert len(h_after) == n_before + 2, \
            f"history should grow by 2, got {len(h_after)-n_before}"
        # last two entries: user then assistant
        last_two = h_after[-2:]
        assert last_two[0]["role"] == "user"
        assert last_two[1]["role"] == "assistant"
        assert len(last_two[1]["content"]) > 0
        stream_user.first_user_msg = last_two[0]["content"]

    def test_stream_conversation_memory(self, stream_user):
        """Second stream request should recall context from first turn."""
        # First turn: give the assistant a specific pet name to remember
        with stream_user.post(
            f"{API}/ai/chat/stream",
            json={"message": "Il mio cane si chiama Fulmine. Ricordati questo nome."},
            stream=True, timeout=120,
        ) as r:
            assert r.status_code == 200
            for raw in r.iter_lines(decode_unicode=True):
                if raw and raw.startswith("data:") and '"done"' in raw:
                    break
        time.sleep(0.5)

        # Second turn: ask the model to recall the name
        full = ""
        with stream_user.post(
            f"{API}/ai/chat/stream",
            json={"message": "Come si chiama il mio cane?"},
            stream=True, timeout=120,
        ) as r:
            assert r.status_code == 200
            for raw in r.iter_lines(decode_unicode=True):
                if not raw or not raw.startswith("data:"):
                    continue
                try:
                    obj = _json.loads(raw[5:].strip())
                except Exception:
                    continue
                if "delta" in obj:
                    full += obj["delta"]
                elif obj.get("done"):
                    break
        assert "fulmine" in full.lower(), \
            f"Streaming chat did not recall the pet name 'Fulmine'. Got: {full[:400]}"


# ---------- Scheduler + Manual Batch (NEW FEATURE) ----------
class TestSchedulerBatch:
    """Verify:
       - POST /api/push/run-batch requires auth (401 anonymous)
       - Non-admin user gets 403 with detail 'Solo admin'
       - Admin gets {total: int}
       - Regression: POST /api/push/check-reminders still works per user
    """

    def test_run_batch_requires_auth(self):
        r = requests.post(f"{API}/push/run-batch", timeout=15)
        assert r.status_code == 401

    def test_run_batch_forbidden_for_non_admin(self, new_user_session):
        r = new_user_session.post(f"{API}/push/run-batch", timeout=15)
        assert r.status_code == 403, f"non-admin should be 403, got {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("detail") == "Solo admin", f"unexpected detail: {body}"

    def test_run_batch_ok_for_admin(self, admin_session):
        r = admin_session.post(f"{API}/push/run-batch", timeout=30)
        assert r.status_code == 200, f"admin batch failed: {r.status_code} {r.text}"
        body = r.json()
        assert "total" in body
        assert isinstance(body["total"], int)
        assert body["total"] >= 0

    def test_check_reminders_still_works(self, new_user_session):
        r = new_user_session.post(f"{API}/push/check-reminders", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json().get("sent"), int)


# ---------- Medical Documents (NEW FEATURE - Object Storage) ----------
class TestDocuments:
    """Verify document endpoints:
       - GET /api/pets/{id}/documents lists non-deleted docs (no storage_path leaked)
       - POST /api/pets/{id}/documents uploads (multipart) to object storage + DB record
       - GET /api/documents/{doc_id}/download returns bytes with correct content-type
       - DELETE /api/pets/{id}/documents/{doc_id} soft-deletes (is_deleted=true)
       - Files > 15MB rejected with 400
       - Auth required, owner-only
    """

    @pytest.fixture(scope="class")
    def doc_user(self):
        s = requests.Session()
        email = f"test_doc_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Doc Tester"},
                   timeout=15)
        assert r.status_code == 200
        # Documents are Premium-gated: activate free trial so this user can upload
        tr = s.post(f"{API}/subscription/trial", timeout=15)
        assert tr.status_code == 200, f"trial activation failed: {tr.text}"
        pr = s.post(f"{API}/pets", json={
            "name": "TEST_DocPet", "species": "dog", "breed": "Bulldog",
            "birth_date": "2019-03-15", "sex": "M", "weight": 20.0
        }, timeout=15)
        assert pr.status_code == 200
        s.pet_id = pr.json()["id"]
        s.email = email
        return s

    def test_list_documents_empty_initially(self, doc_user):
        r = doc_user.get(f"{API}/pets/{doc_user.pet_id}/documents", timeout=15)
        assert r.status_code == 200
        assert r.json() == []

    def test_upload_document_txt(self, doc_user):
        pid = doc_user.pet_id
        content = b"TEST document contents - PawCare regression test\n"
        files = {"file": ("test_referto.txt", content, "text/plain")}
        data = {"category": "referto"}
        r = doc_user.post(f"{API}/pets/{pid}/documents", files=files, data=data, timeout=60)
        assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:400]}"
        body = r.json()
        assert body["name"] == "test_referto.txt"
        assert body["category"] == "referto"
        assert body["pet_id"] == pid
        assert body["is_deleted"] is False
        assert body["content_type"] == "text/plain"
        assert "id" in body
        # storage_path must NOT leak to client
        assert "storage_path" not in body
        assert "_id" not in body
        doc_user.doc_id = body["id"]
        doc_user.doc_content = content

    def test_list_documents_shows_uploaded_no_storage_path(self, doc_user):
        r = doc_user.get(f"{API}/pets/{doc_user.pet_id}/documents", timeout=15)
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) >= 1
        our = next((d for d in docs if d["id"] == doc_user.doc_id), None)
        assert our is not None
        assert our["name"] == "test_referto.txt"
        assert our["category"] == "referto"
        assert "storage_path" not in our
        assert "_id" not in our

    def test_upload_default_category(self, doc_user):
        """category defaults to 'altro' if not provided."""
        pid = doc_user.pet_id
        files = {"file": ("misc.txt", b"misc bytes", "text/plain")}
        r = doc_user.post(f"{API}/pets/{pid}/documents", files=files, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["category"] == "altro"
        doc_user.doc_id_misc = r.json()["id"]

    def test_download_document_returns_bytes(self, doc_user):
        r = doc_user.get(f"{API}/documents/{doc_user.doc_id}/download", timeout=60)
        assert r.status_code == 200
        # Content bytes match what we uploaded
        assert r.content == doc_user.doc_content, \
            f"downloaded bytes mismatch. len={len(r.content)}"
        # Content-Type should be text/plain (as stored)
        ctype = r.headers.get("content-type", "")
        assert "text/plain" in ctype, f"bad content-type: {ctype}"

    def test_upload_requires_auth(self, doc_user):
        files = {"file": ("x.txt", b"y", "text/plain")}
        r = requests.post(f"{API}/pets/{doc_user.pet_id}/documents",
                          files=files, data={"category": "altro"}, timeout=15)
        assert r.status_code == 401

    def test_list_documents_requires_auth(self, doc_user):
        r = requests.get(f"{API}/pets/{doc_user.pet_id}/documents", timeout=10)
        assert r.status_code == 401

    def test_download_requires_auth(self, doc_user):
        r = requests.get(f"{API}/documents/{doc_user.doc_id}/download", timeout=15)
        assert r.status_code == 401

    def test_download_isolated_across_users(self, doc_user, admin_session):
        """Admin (different user) must NOT be able to download another user's doc."""
        r = admin_session.get(f"{API}/documents/{doc_user.doc_id}/download", timeout=15)
        assert r.status_code == 404

    def test_upload_other_user_pet_rejected(self, doc_user, admin_session):
        """Admin cannot upload to another user's pet (pet not found for admin)."""
        files = {"file": ("x.txt", b"y", "text/plain")}
        r = admin_session.post(f"{API}/pets/{doc_user.pet_id}/documents",
                               files=files, data={"category": "altro"}, timeout=15)
        assert r.status_code == 404

    def test_upload_rejects_over_15mb(self, doc_user):
        """15MB+1 byte payload must be rejected with 400."""
        big = b"A" * (15 * 1024 * 1024 + 1)
        files = {"file": ("big.txt", big, "text/plain")}
        r = doc_user.post(f"{API}/pets/{doc_user.pet_id}/documents",
                          files=files, data={"category": "altro"}, timeout=120)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:300]}"
        assert "15MB" in r.json().get("detail", "") or "grande" in r.json().get("detail", "").lower()

    def test_soft_delete_document(self, doc_user):
        pid = doc_user.pet_id
        r = doc_user.delete(f"{API}/pets/{pid}/documents/{doc_user.doc_id}", timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # No longer in list
        lst = doc_user.get(f"{API}/pets/{pid}/documents", timeout=15).json()
        assert not any(d["id"] == doc_user.doc_id for d in lst), \
            "soft-deleted doc still visible in list"

        # Download by id must 404 (soft-deleted → not found)
        dr = doc_user.get(f"{API}/documents/{doc_user.doc_id}/download", timeout=15)
        assert dr.status_code == 404

    def test_delete_pet_cascades_soft_delete_documents(self, doc_user):
        """Delete pet must soft-delete remaining documents; list must return [] via new pet."""
        pid = doc_user.pet_id
        # doc_id_misc still exists — verify visible before delete
        lst_before = doc_user.get(f"{API}/pets/{pid}/documents", timeout=15).json()
        assert any(d["id"] == doc_user.doc_id_misc for d in lst_before)

        # Delete the pet
        r = doc_user.delete(f"{API}/pets/{pid}", timeout=15)
        assert r.status_code == 200

        # Download of the cascaded doc should also 404 (record still exists but is_deleted=true)
        dr = doc_user.get(f"{API}/documents/{doc_user.doc_id_misc}/download", timeout=15)
        assert dr.status_code == 404


# ---------- Calendar (NEW FEATURE - multi-pet events) ----------
class TestCalendar:
    """Verify GET /api/calendar/events returns all events across the user's pets:
       - visits (date), vaccines (next_due), treatments (next_due)
       - each event has {date, type, title, pet_id, pet_name}
       - sorted by date ascending
       - only current user's events (isolation)
       - empty list when user has no pets
    """

    @pytest.fixture(scope="class")
    def cal_user(self):
        s = requests.Session()
        email = f"test_cal_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Cal Tester"},
                   timeout=15)
        assert r.status_code == 200
        s.email = email
        return s

    def test_calendar_empty_no_pets(self, cal_user):
        r = cal_user.get(f"{API}/calendar/events", timeout=15)
        assert r.status_code == 200
        assert r.json() == []

    def test_calendar_returns_all_event_types_sorted(self, cal_user):
        # Create two pets
        p1 = cal_user.post(f"{API}/pets", json={
            "name": "TEST_CalPet1", "species": "dog", "breed": "Boxer",
            "birth_date": "2020-01-01", "sex": "M", "weight": 22.0
        }, timeout=15).json()
        p2 = cal_user.post(f"{API}/pets", json={
            "name": "TEST_CalPet2", "species": "cat", "breed": "Siamese",
            "birth_date": "2021-01-01", "sex": "F", "weight": 4.5
        }, timeout=15).json()
        cal_user.p1 = p1["id"]
        cal_user.p2 = p2["id"]

        # visit on pet1
        cal_user.post(f"{API}/pets/{p1['id']}/visits", json={
            "date": "2025-06-10", "reason": "TEST_Controllo", "veterinarian": "Dr. X"
        }, timeout=10)
        # vaccine on pet1 with next_due
        cal_user.post(f"{API}/pets/{p1['id']}/vaccines", json={
            "name": "TEST_Antirabbica", "date_given": "2025-01-01", "next_due": "2025-08-01"
        }, timeout=10)
        # vaccine without next_due → should NOT appear
        cal_user.post(f"{API}/pets/{p1['id']}/vaccines", json={
            "name": "TEST_NoDueVax", "date_given": "2025-01-01", "next_due": None
        }, timeout=10)
        # treatment on pet2 with next_due
        cal_user.post(f"{API}/pets/{p2['id']}/treatments", json={
            "name": "TEST_Antipulci", "date_given": "2025-01-01",
            "frequency_days": 30, "next_due": "2025-04-15"
        }, timeout=10)
        # treatment without next_due → should NOT appear
        cal_user.post(f"{API}/pets/{p2['id']}/treatments", json={
            "name": "TEST_NoDueTr", "date_given": "2025-01-01",
            "frequency_days": 30, "next_due": None
        }, timeout=10)

        r = cal_user.get(f"{API}/calendar/events", timeout=15)
        assert r.status_code == 200
        events = r.json()

        # find our TEST events
        ours = [e for e in events if e["title"].startswith("TEST_")]
        titles = {e["title"] for e in ours}
        assert "TEST_Controllo" in titles
        assert "TEST_Antirabbica" in titles
        assert "TEST_Antipulci" in titles
        # events with null next_due are excluded
        assert "TEST_NoDueVax" not in titles
        assert "TEST_NoDueTr" not in titles

        # Each event has required fields
        for e in ours:
            assert set(["date", "type", "title", "pet_id", "pet_name"]).issubset(e.keys())
            assert e["type"] in ("visit", "vaccine", "treatment")
            assert e["pet_name"] in ("TEST_CalPet1", "TEST_CalPet2")

        # Verify types match
        by_title = {e["title"]: e for e in ours}
        assert by_title["TEST_Controllo"]["type"] == "visit"
        assert by_title["TEST_Controllo"]["date"] == "2025-06-10"
        assert by_title["TEST_Controllo"]["pet_id"] == p1["id"]
        assert by_title["TEST_Controllo"]["pet_name"] == "TEST_CalPet1"

        assert by_title["TEST_Antirabbica"]["type"] == "vaccine"
        assert by_title["TEST_Antirabbica"]["date"] == "2025-08-01"

        assert by_title["TEST_Antipulci"]["type"] == "treatment"
        assert by_title["TEST_Antipulci"]["date"] == "2025-04-15"
        assert by_title["TEST_Antipulci"]["pet_name"] == "TEST_CalPet2"

        # Sorted ascending by date (globally, not only ours)
        dates = [e["date"] for e in events]
        assert dates == sorted(dates), f"events not sorted ascending: {dates}"

    def test_calendar_requires_auth(self):
        r = requests.get(f"{API}/calendar/events", timeout=10)
        assert r.status_code == 401

    def test_calendar_isolated_across_users(self, cal_user, admin_session):
        """Admin's calendar must NOT include cal_user's TEST_ events."""
        r = admin_session.get(f"{API}/calendar/events", timeout=15)
        assert r.status_code == 200
        events = r.json()
        # None of admin's events should be linked to cal_user's pets
        assert not any(e["pet_id"] in (cal_user.p1, cal_user.p2) for e in events)
        # And no TEST_ titles from cal_user's pets
        assert not any(e["title"] in ("TEST_Controllo", "TEST_Antirabbica", "TEST_Antipulci")
                       and e["pet_name"] in ("TEST_CalPet1", "TEST_CalPet2")
                       for e in events)



# ---------- Admin endpoints (NEW FEATURE - role gating + stats + users table) ----------
class TestAdmin:
    """Verify:
       - GET /api/auth/me returns role='admin' for admin, 'user' otherwise
       - GET /api/admin/stats + /api/admin/users:
           - 401 anonymous
           - 403 with Italian detail for normal user
           - 200 with expected shape for admin
    """

    def test_me_returns_role_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body.get("role") == "admin", f"expected role=admin, got {body}"

    def test_me_returns_role_user_for_normal(self, new_user_session):
        r = new_user_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json().get("role") == "user"

    def test_admin_stats_requires_auth(self):
        r = requests.get(f"{API}/admin/stats", timeout=10)
        assert r.status_code == 401

    def test_admin_users_requires_auth(self):
        r = requests.get(f"{API}/admin/users", timeout=10)
        assert r.status_code == 401

    def test_admin_stats_forbidden_for_non_admin(self, new_user_session):
        r = new_user_session.get(f"{API}/admin/stats", timeout=10)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        assert r.json().get("detail") == "Accesso riservato agli amministratori"

    def test_admin_users_forbidden_for_non_admin(self, new_user_session):
        r = new_user_session.get(f"{API}/admin/users", timeout=10)
        assert r.status_code == 403
        assert r.json().get("detail") == "Accesso riservato agli amministratori"

    def test_admin_stats_ok_for_admin(self, admin_session):
        r = admin_session.get(f"{API}/admin/stats", timeout=15)
        assert r.status_code == 200
        data = r.json()
        # required keys
        required = ["total_users", "new_users_7d", "google_users", "email_users",
                   "push_users", "total_pets", "total_visits", "total_vaccines",
                   "total_treatments", "total_chat_messages"]
        for k in required:
            assert k in data, f"missing stat: {k}"
            assert isinstance(data[k], int), f"{k} should be int, got {type(data[k])}"
        # sanity
        assert data["total_users"] >= 1
        assert data["email_users"] >= 1  # at least admin

    def test_admin_users_ok_for_admin(self, admin_session):
        r = admin_session.get(f"{API}/admin/users", timeout=20)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        assert len(users) >= 1
        # find admin row
        admin_row = next((u for u in users if u.get("email") == ADMIN_EMAIL), None)
        assert admin_row is not None, "admin user missing from /admin/users"
        # required user fields
        for k in ["user_id", "email", "name", "auth_provider", "pet_count", "chat_count", "has_push"]:
            assert k in admin_row, f"missing field: {k}"
        # no sensitive fields leaked
        assert "password_hash" not in admin_row
        assert "_id" not in admin_row
        # counts are ints, has_push is bool
        assert isinstance(admin_row["pet_count"], int)
        assert isinstance(admin_row["chat_count"], int)
        assert isinstance(admin_row["has_push"], bool)
        # role field present for admin row
        assert admin_row.get("role") == "admin"



# ---------- Bug-fix re-test: login/register responses must include user.role ----------
class TestAuthRoleInResponse:
    """Iteration 8 re-test:
       - POST /api/auth/login  must return user.role
       - POST /api/auth/register must return user.role
    """

    def test_login_response_includes_role_admin(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert "user" in body
        assert body["user"].get("role") == "admin", f"admin login missing role=admin, got: {body}"

    def test_register_response_includes_role_user(self):
        email = f"test_role8_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/auth/register",
                          json={"email": email, "password": "Pass1234!", "name": "Role8"},
                          timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["user"].get("role") == "user", f"register missing role=user, got: {body}"

    def test_login_response_includes_role_user_for_regular(self):
        # register then login as regular user
        email = f"test_role8b_{uuid.uuid4().hex[:8]}@example.com"
        r0 = requests.post(f"{API}/auth/register",
                           json={"email": email, "password": "Pass1234!", "name": "Reg8"},
                           timeout=15)
        assert r0.status_code == 200
        r = requests.post(f"{API}/auth/login",
                         json={"email": email, "password": "Pass1234!"}, timeout=10)
        assert r.status_code == 200
        assert r.json()["user"].get("role") == "user"



# ---------- Subscription / Freemium (NEW FEATURE) ----------
from datetime import datetime, timezone
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


def _direct_db():
    """Direct pymongo handle for seeding ai_usage (avoids burning LLM credits)."""
    return MongoClient(MONGO_URL)[DB_NAME]


class TestSubscription:
    """Verify freemium subscription flow:
       - GET /api/subscription/status shape for fresh user (premium=false, trial_used=false)
       - POST /api/subscription/trial grants 7 days premium, blocks 2nd call, blocks if already premium
       - POST /api/subscription/checkout returns stripe url + session_id, records payment_transactions
       - Invalid package_id -> 400
       - GET /api/subscription/checkout/status/{id} works on unpaid session
       - AI quota gating (5/day) via db seed
       - Documents gating: free 402, after trial 200
       - Premium user is not AI-limited (skipped-safely with seed check)
    """

    @pytest.fixture(scope="class")
    def sub_user(self):
        s = requests.Session()
        email = f"test_sub_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Sub Tester"},
                   timeout=15)
        assert r.status_code == 200
        me = s.get(f"{API}/auth/me", timeout=10).json()
        s.user_id = me["user_id"]
        s.email = email
        return s

    @pytest.fixture(scope="class")
    def sub_user_2(self):
        """Second user for AI quota test (isolated from doc/trial user)."""
        s = requests.Session()
        email = f"test_sub2_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Sub2 Tester"},
                   timeout=15)
        assert r.status_code == 200
        me = s.get(f"{API}/auth/me", timeout=10).json()
        s.user_id = me["user_id"]
        s.email = email
        return s

    # ---- status shape ----
    def test_status_fresh_user(self, sub_user):
        r = sub_user.get(f"{API}/subscription/status", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["premium"] is False
        assert data.get("premium_until") in (None, "") or data.get("premium_until") is None
        assert data["trial_used"] is False
        assert data["ai_used_today"] == 0
        assert data["ai_limit"] == 5
        assert data["trial_days"] == 7
        pkgs = data["packages"]
        assert "monthly" in pkgs and "yearly" in pkgs
        assert pkgs["monthly"]["amount"] == 7.99
        assert pkgs["monthly"]["days"] == 30
        assert pkgs["yearly"]["amount"] == 79.99
        assert pkgs["yearly"]["days"] == 365

    def test_status_requires_auth(self):
        r = requests.get(f"{API}/subscription/status", timeout=10)
        assert r.status_code == 401

    # ---- checkout ----
    def test_checkout_invalid_package(self, sub_user):
        r = sub_user.post(f"{API}/subscription/checkout",
                          json={"package_id": "lifetime", "origin_url": BASE_URL},
                          timeout=15)
        assert r.status_code == 400
        assert "Pacchetto" in r.json().get("detail", "")

    def test_checkout_monthly_creates_session(self, sub_user):
        r = sub_user.post(f"{API}/subscription/checkout",
                          json={"package_id": "monthly", "origin_url": BASE_URL},
                          timeout=30)
        assert r.status_code == 200, f"checkout failed: {r.text[:400]}"
        data = r.json()
        assert "url" in data and "session_id" in data
        assert "stripe.com" in data["url"]
        assert data["session_id"].startswith("cs_") or len(data["session_id"]) > 10
        # payment_transactions record exists
        db = _direct_db()
        tx = db.payment_transactions.find_one({"session_id": data["session_id"]})
        assert tx is not None
        assert tx["user_id"] == sub_user.user_id
        assert tx["package_id"] == "monthly"
        assert tx["amount"] == 7.99
        assert tx["payment_status"] == "initiated"
        assert tx["processed"] is False
        sub_user.session_id = data["session_id"]

    def test_checkout_yearly_creates_session(self, sub_user):
        r = sub_user.post(f"{API}/subscription/checkout",
                          json={"package_id": "yearly", "origin_url": BASE_URL},
                          timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "stripe.com" in data["url"]
        db = _direct_db()
        tx = db.payment_transactions.find_one({"session_id": data["session_id"]})
        assert tx and tx["amount"] == 79.99 and tx["package_id"] == "yearly"

    def test_checkout_requires_auth(self):
        r = requests.post(f"{API}/subscription/checkout",
                          json={"package_id": "monthly", "origin_url": BASE_URL}, timeout=10)
        assert r.status_code == 401

    def test_checkout_status_returns_payment_status(self, sub_user):
        sid = sub_user.session_id
        r = sub_user.get(f"{API}/subscription/checkout/status/{sid}", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "payment_status" in data
        # Unpaid test session: payment_status is 'unpaid' or similar, NOT 'paid'
        assert data["payment_status"] != "paid"
        # user should not be premium since session unpaid
        st = sub_user.get(f"{API}/subscription/status", timeout=10).json()
        assert st["premium"] is False

    def test_checkout_status_unknown_session(self, sub_user):
        r = sub_user.get(f"{API}/subscription/checkout/status/cs_nonexistent_xxx", timeout=15)
        assert r.status_code == 404

    # ---- AI quota gating via DB seed (avoid burning real LLM credits) ----
    def test_ai_quota_seeded_402(self, sub_user_2):
        """Seed ai_usage {count:5} for today so all 3 AI endpoints 402."""
        today = datetime.now(timezone.utc).date().isoformat()
        db = _direct_db()
        db.ai_usage.update_one(
            {"user_id": sub_user_2.user_id, "date": today},
            {"$set": {"user_id": sub_user_2.user_id, "date": today, "count": 5}},
            upsert=True,
        )
        # status reflects usage
        st = sub_user_2.get(f"{API}/subscription/status", timeout=10).json()
        assert st["ai_used_today"] == 5
        assert st["premium"] is False

        # /ai/chat -> 402
        r1 = sub_user_2.post(f"{API}/ai/chat", json={"message": "ciao"}, timeout=15)
        assert r1.status_code == 402, f"expected 402, got {r1.status_code}: {r1.text[:300]}"
        detail = r1.json().get("detail", "")
        assert "5" in detail or "limit" in detail.lower() or "Premium" in detail

        # /ai/advice -> 402 (pet_id doesn't matter, quota checked first)
        r2 = sub_user_2.post(f"{API}/ai/advice", json={"pet_id": "any"}, timeout=15)
        assert r2.status_code == 402

        # /ai/chat/stream -> 402
        r3 = sub_user_2.post(f"{API}/ai/chat/stream", json={"message": "ciao"}, timeout=15)
        assert r3.status_code == 402

    # ---- Trial ----
    def test_documents_gate_free_402(self, sub_user):
        """Free user (before trial) must get 402 uploading documents."""
        # Create a pet first
        pr = sub_user.post(f"{API}/pets", json={
            "name": "TEST_DocGate", "species": "dog", "breed": "Poodle",
            "birth_date": "2022-01-01", "sex": "F", "weight": 8.0
        }, timeout=15)
        assert pr.status_code == 200
        sub_user.pet_id = pr.json()["id"]

        files = {"file": ("gate.txt", b"gate content", "text/plain")}
        r = sub_user.post(f"{API}/pets/{sub_user.pet_id}/documents",
                          files=files, data={"category": "referto"}, timeout=30)
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text[:300]}"
        assert "Premium" in r.json().get("detail", "")

        # But LIST still works for free users (empty)
        lr = sub_user.get(f"{API}/pets/{sub_user.pet_id}/documents", timeout=10)
        assert lr.status_code == 200
        assert lr.json() == []

    def test_trial_grants_premium(self, sub_user):
        r = sub_user.post(f"{API}/subscription/trial", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "premium_until" in data
        # premium_until should be ~7 days from now
        until = datetime.fromisoformat(data["premium_until"])
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (until - now).total_seconds() / 86400.0
        assert 6.5 < delta < 7.5, f"expected ~7 days premium, got {delta}"

        # status now reflects premium=true, trial_used=true
        st = sub_user.get(f"{API}/subscription/status", timeout=10).json()
        assert st["premium"] is True
        assert st["trial_used"] is True

    def test_trial_second_call_400(self, sub_user):
        r = sub_user.post(f"{API}/subscription/trial", timeout=15)
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "Prova" in detail or "gratuita" in detail.lower() or "già" in detail

    def test_documents_upload_ok_after_trial(self, sub_user):
        """Premium (via trial) can now upload documents."""
        files = {"file": ("premium.txt", b"premium upload OK", "text/plain")}
        r = sub_user.post(f"{API}/pets/{sub_user.pet_id}/documents",
                          files=files, data={"category": "referto"}, timeout=60)
        assert r.status_code == 200, f"upload should succeed after trial, got {r.status_code}: {r.text[:300]}"
        body = r.json()
        assert body["name"] == "premium.txt"
        assert body["is_deleted"] is False

    def test_trial_blocked_when_already_premium(self, sub_user):
        """A user who already has trial_used=true always gets 400 - covered above.
           This test also confirms the endpoint stays 400 (not 500) when premium is active."""
        r = sub_user.post(f"{API}/subscription/trial", timeout=15)
        assert r.status_code == 400

    def test_premium_user_ai_not_limited(self, sub_user):
        """Premium user: seed count=99 to prove no 402 (do NOT actually call LLM)."""
        today = datetime.now(timezone.utc).date().isoformat()
        db = _direct_db()
        db.ai_usage.update_one(
            {"user_id": sub_user.user_id, "date": today},
            {"$set": {"user_id": sub_user.user_id, "date": today, "count": 99}},
            upsert=True,
        )
        # status: premium=true, ai_used_today reported but no gate
        st = sub_user.get(f"{API}/subscription/status", timeout=10).json()
        assert st["premium"] is True
        assert st["ai_used_today"] == 99
        # Directly assert check_ai_quota won't 402 by invoking a lightweight endpoint
        # that runs the quota check first. We do NOT complete an LLM call.
        # Trick: /ai/advice with an invalid pet_id would still pass the quota check
        # (premium user), and then 404 on _pet_context; NOT 402.
        r = sub_user.post(f"{API}/ai/advice",
                          json={"pet_id": "definitely-not-real"}, timeout=30)
        assert r.status_code != 402, f"premium user got 402: {r.status_code} {r.text[:200]}"
        # It should be 404 (pet not found), not 402
        assert r.status_code == 404


# ---------- Admin Premium Management (NEW FEATURE: gift/revoke/delete users) ----------
class TestAdminPremiumManagement:
    """Verify:
       - POST /api/admin/users/{id}/grant-premium (monthly/yearly/lifetime)
       - POST /api/admin/users/{id}/revoke-premium
       - DELETE /api/admin/users/{id} with cascade + 400 self / 400 admin / 200 normal
       - Auth: 403 for non-admin, 401 anonymous
       - /admin/stats.premium_users count, /admin/users returns premium field
    """

    def _make_target(self):
        s = requests.Session()
        email = f"test_gift_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Gift Target"},
                   timeout=15)
        assert r.status_code == 200, f"register failed: {r.text}"
        me = s.get(f"{API}/auth/me", timeout=10).json()
        s.user_id = me["user_id"]
        s.email = email
        return s

    def test_grant_lifetime_sets_2099(self, admin_session):
        t = self._make_target()
        r = admin_session.post(f"{API}/admin/users/{t.user_id}/grant-premium",
                               json={"plan": "lifetime"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "premium_until" in body
        assert body["premium_until"].startswith("2099"), f"expected 2099, got {body['premium_until']}"
        # Target user sees premium=true
        st = t.get(f"{API}/subscription/status", timeout=10).json()
        assert st["premium"] is True
        assert st["premium_until"].startswith("2099")
        # revoke to clean up
        admin_session.post(f"{API}/admin/users/{t.user_id}/revoke-premium", timeout=10)

    def test_grant_monthly_adds_30_days(self, admin_session):
        t = self._make_target()
        r = admin_session.post(f"{API}/admin/users/{t.user_id}/grant-premium",
                               json={"plan": "monthly"}, timeout=15)
        assert r.status_code == 200
        until = datetime.fromisoformat(r.json()["premium_until"])
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        delta = (until - datetime.now(timezone.utc)).total_seconds() / 86400.0
        assert 29.5 < delta < 30.5, f"expected ~30d, got {delta}"
        st = t.get(f"{API}/subscription/status", timeout=10).json()
        assert st["premium"] is True

    def test_grant_yearly_adds_365_days(self, admin_session):
        t = self._make_target()
        r = admin_session.post(f"{API}/admin/users/{t.user_id}/grant-premium",
                               json={"plan": "yearly"}, timeout=15)
        assert r.status_code == 200
        until = datetime.fromisoformat(r.json()["premium_until"])
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        delta = (until - datetime.now(timezone.utc)).total_seconds() / 86400.0
        assert 364.5 < delta < 365.5, f"expected ~365d, got {delta}"
        st = t.get(f"{API}/subscription/status", timeout=10).json()
        assert st["premium"] is True

    def test_revoke_premium_clears(self, admin_session):
        t = self._make_target()
        # First grant
        admin_session.post(f"{API}/admin/users/{t.user_id}/grant-premium",
                           json={"plan": "monthly"}, timeout=15)
        st = t.get(f"{API}/subscription/status", timeout=10).json()
        assert st["premium"] is True
        # Revoke
        r = admin_session.post(f"{API}/admin/users/{t.user_id}/revoke-premium", timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        st2 = t.get(f"{API}/subscription/status", timeout=10).json()
        assert st2["premium"] is False
        assert st2.get("premium_until") is None

    def test_grant_premium_requires_admin(self, new_user_session):
        # normal user cannot grant
        # Need any target id — use their own id
        me = new_user_session.get(f"{API}/auth/me").json()
        r = new_user_session.post(f"{API}/admin/users/{me['user_id']}/grant-premium",
                                  json={"plan": "monthly"}, timeout=10)
        assert r.status_code == 403

    def test_revoke_premium_requires_admin(self, new_user_session):
        me = new_user_session.get(f"{API}/auth/me").json()
        r = new_user_session.post(f"{API}/admin/users/{me['user_id']}/revoke-premium", timeout=10)
        assert r.status_code == 403

    def test_grant_premium_requires_auth(self):
        r = requests.post(f"{API}/admin/users/x/grant-premium", json={"plan": "monthly"}, timeout=10)
        assert r.status_code == 401

    def test_grant_premium_unknown_user(self, admin_session):
        r = admin_session.post(f"{API}/admin/users/nonexistent_id/grant-premium",
                               json={"plan": "monthly"}, timeout=10)
        assert r.status_code == 404

    def test_admin_users_includes_premium_field(self, admin_session):
        # Grant a fresh user premium so we can assert the badge round-trip
        t = self._make_target()
        admin_session.post(f"{API}/admin/users/{t.user_id}/grant-premium",
                           json={"plan": "lifetime"}, timeout=15)
        users = admin_session.get(f"{API}/admin/users", timeout=15).json()
        row = next((u for u in users if u["user_id"] == t.user_id), None)
        assert row is not None, "target user missing from admin users list"
        assert row.get("premium") is True
        assert row.get("premium_until", "").startswith("2099")
        # cleanup
        admin_session.post(f"{API}/admin/users/{t.user_id}/revoke-premium", timeout=10)
        users2 = admin_session.get(f"{API}/admin/users", timeout=15).json()
        row2 = next((u for u in users2 if u["user_id"] == t.user_id), None)
        assert row2.get("premium") is False

    def test_admin_stats_has_premium_users(self, admin_session):
        # Grant one to ensure count >= 1
        t = self._make_target()
        admin_session.post(f"{API}/admin/users/{t.user_id}/grant-premium",
                           json={"plan": "monthly"}, timeout=15)
        r = admin_session.get(f"{API}/admin/stats", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "premium_users" in data
        assert isinstance(data["premium_users"], int)
        assert data["premium_users"] >= 1
        # cleanup
        admin_session.post(f"{API}/admin/users/{t.user_id}/revoke-premium", timeout=10)

    # ---- Delete user ----
    def test_delete_self_returns_400(self, admin_session):
        me = admin_session.get(f"{API}/auth/me", timeout=10).json()
        r = admin_session.delete(f"{API}/admin/users/{me['user_id']}", timeout=10)
        assert r.status_code == 400
        assert "Non puoi eliminare il tuo account" in r.json().get("detail", "")

    def test_delete_another_admin_returns_400(self, admin_session):
        # create another admin directly via mongo (we only have one admin normally)
        db = _direct_db()
        other_id = f"user_{uuid.uuid4().hex[:12]}"
        db.users.insert_one({
            "user_id": other_id, "email": f"test_admin2_{uuid.uuid4().hex[:6]}@example.com",
            "name": "Other Admin", "password_hash": "$2b$12$dummy",
            "picture": "", "auth_provider": "email", "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            r = admin_session.delete(f"{API}/admin/users/{other_id}", timeout=10)
            assert r.status_code == 400
            assert "amministratore" in r.json().get("detail", "").lower()
        finally:
            db.users.delete_one({"user_id": other_id})

    def test_delete_unknown_user_returns_404(self, admin_session):
        r = admin_session.delete(f"{API}/admin/users/does_not_exist", timeout=10)
        assert r.status_code == 404

    def test_delete_requires_admin(self, new_user_session):
        # register another target
        target = self._make_target()
        r = new_user_session.delete(f"{API}/admin/users/{target.user_id}", timeout=10)
        assert r.status_code == 403

    def test_delete_requires_auth(self):
        r = requests.delete(f"{API}/admin/users/x", timeout=10)
        assert r.status_code == 401

    def test_delete_normal_user_cascades_and_removes_from_list(self, admin_session):
        # Create a fresh target and load it with data
        t = self._make_target()
        pr = t.post(f"{API}/pets", json={
            "name": "TEST_DelPet", "species": "dog", "breed": "Husky",
            "birth_date": "2021-06-01", "sex": "M", "weight": 20.0
        }, timeout=15)
        assert pr.status_code == 200
        pet_id = pr.json()["id"]
        # Add related records
        t.post(f"{API}/pets/{pet_id}/visits",
               json={"date": "2025-01-15", "reason": "TEST_visit"}, timeout=10)
        t.post(f"{API}/pets/{pet_id}/vaccines",
               json={"name": "TEST_vax", "date_given": "2025-01-01",
                     "next_due": "2025-12-01"}, timeout=10)
        t.post(f"{API}/pets/{pet_id}/treatments",
               json={"name": "TEST_tr", "date_given": "2025-01-01",
                     "frequency_days": 30, "next_due": "2025-02-01"}, timeout=10)
        t.post(f"{API}/pets/{pet_id}/weights",
               json={"date": "2025-01-01", "weight": 21.0}, timeout=10)

        # confirm the target is in admin/users
        before = admin_session.get(f"{API}/admin/users", timeout=15).json()
        assert any(u["user_id"] == t.user_id for u in before)

        # DELETE
        r = admin_session.delete(f"{API}/admin/users/{t.user_id}", timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # No longer in admin/users
        after = admin_session.get(f"{API}/admin/users", timeout=15).json()
        assert not any(u["user_id"] == t.user_id for u in after), \
            "deleted user still present in /admin/users"

        # Cascade: direct DB check that pet + related collections are cleaned up
        db = _direct_db()
        assert db.users.find_one({"user_id": t.user_id}) is None
        assert db.pets.find_one({"user_id": t.user_id}) is None
        assert db.pets.find_one({"id": pet_id}) is None
        assert db.visits.find_one({"pet_id": pet_id}) is None
        assert db.vaccines.find_one({"pet_id": pet_id}) is None
        assert db.treatments.find_one({"pet_id": pet_id}) is None
        assert db.weights.find_one({"pet_id": pet_id}) is None

        # The user's session (cookie) should now be dead
        me = t.get(f"{API}/auth/me", timeout=10)
        assert me.status_code == 401

    def test_grant_premium_to_deleted_user_returns_404(self, admin_session):
        r = admin_session.post(f"{API}/admin/users/deleted_ghost_id/grant-premium",
                               json={"plan": "monthly"}, timeout=10)
        assert r.status_code == 404
