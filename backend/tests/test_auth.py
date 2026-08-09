"""Tests for authentication and role enforcement.

The most valuable test in this file is the sweep at the bottom: it walks every
registered API route and asserts none of them answers without a token. A guard
applied by hand to each endpoint is a guard that will be forgotten on the next
one added.
"""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from lynjax.core.config import Settings, get_settings
from lynjax.core.database import Database
from lynjax.core.deps import get_db, get_vault
from lynjax.core.security import (
    InvalidTokenError,
    WeakPasswordError,
    create_access_token,
    decode_access_token,
    has_privilege,
    hash_password,
    validate_password,
    verify_password,
)
from lynjax.main import app
from lynjax.services.users import (
    DuplicateUserError,
    InvalidEmailError,
    UserError,
    UserRepository,
)
from lynjax.services.vault import CredentialVault

MASTER_KEY = "vLQ5wYAJc6qHhCUW3wRDGxQ0cWQFWpQxNKZbCKzE1yA="
SECRET = "test-secret-key-for-signing-tokens-long-enough-for-hs256"
GOOD_PASSWORD = "correct-horse-battery"


# ─── Primitives ───


class TestPasswordPolicy:
    def test_a_short_password_is_rejected(self):
        with pytest.raises(WeakPasswordError, match="at least 12"):
            validate_password("short")

    def test_an_obvious_password_is_rejected(self):
        with pytest.raises(WeakPasswordError, match="credential-guessing"):
            validate_password("password123")

    def test_a_password_longer_than_bcrypt_handles_is_rejected(self):
        """bcrypt truncates at 72 bytes; accepting more gives false confidence."""
        with pytest.raises(WeakPasswordError, match="72 bytes"):
            validate_password("a" * 73)

    def test_a_reasonable_password_is_accepted(self):
        validate_password(GOOD_PASSWORD)


class TestHashing:
    def test_a_password_round_trips(self):
        assert verify_password(GOOD_PASSWORD, hash_password(GOOD_PASSWORD))

    def test_a_wrong_password_is_rejected(self):
        assert (
            verify_password("wrong-password-x", hash_password(GOOD_PASSWORD)) is False
        )

    def test_the_hash_does_not_contain_the_password(self):
        assert GOOD_PASSWORD not in hash_password(GOOD_PASSWORD)

    def test_the_same_password_hashes_differently_each_time(self):
        assert hash_password(GOOD_PASSWORD) != hash_password(GOOD_PASSWORD)

    def test_a_corrupt_stored_hash_reads_as_wrong_password(self):
        """It must not raise: a caller could mistake that for a server fault."""
        assert verify_password(GOOD_PASSWORD, "not-a-bcrypt-hash") is False


class TestTokens:
    def test_a_token_round_trips(self):
        token = create_access_token(subject="a@b.com", role="admin", secret=SECRET)

        payload = decode_access_token(token, SECRET)

        assert payload["sub"] == "a@b.com"
        assert payload["role"] == "admin"

    def test_a_token_signed_with_another_key_is_rejected(self):
        token = create_access_token(subject="a@b.com", role="admin", secret=SECRET)

        with pytest.raises(InvalidTokenError):
            decode_access_token(token, "a-different-secret-also-long-enough-x")

    def test_an_expired_token_says_so(self):
        token = create_access_token(
            subject="a@b.com",
            role="admin",
            secret=SECRET,
            expires_in=timedelta(seconds=-1),
        )

        with pytest.raises(InvalidTokenError, match="expired"):
            decode_access_token(token, SECRET)

    def test_an_unsigned_token_is_rejected(self):
        """The alg:none family of bypasses, blocked by pinning the algorithm."""
        forged = jwt.encode(
            {"sub": "a@b.com", "role": "admin"}, key="", algorithm="none"
        )

        with pytest.raises(InvalidTokenError):
            decode_access_token(forged, SECRET)

    def test_garbage_is_rejected(self):
        with pytest.raises(InvalidTokenError):
            decode_access_token("not.a.token", SECRET)


class TestRoleRanking:
    @pytest.mark.parametrize(
        ("role", "minimum", "expected"),
        [
            ("admin", "viewer", True),
            ("admin", "operator", True),
            ("admin", "admin", True),
            ("operator", "viewer", True),
            ("operator", "operator", True),
            ("operator", "admin", False),
            ("viewer", "viewer", True),
            ("viewer", "operator", False),
            ("nonsense", "viewer", False),
        ],
    )
    def test_privilege_is_ordered(self, role, minimum, expected):
        assert has_privilege(role, minimum) is expected


# ─── Repository ───


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "auth.db")
    await database.connect()
    try:
        yield database
    finally:
        await database.disconnect()


@pytest.fixture
def users(db) -> UserRepository:
    return UserRepository(db)


class TestUserRepository:
    async def test_a_new_install_has_no_accounts(self, users):
        assert await users.count() == 0

    async def test_a_created_user_can_authenticate(self, users):
        await users.create(email="a@b.com", password=GOOD_PASSWORD, role="admin")

        assert (await users.authenticate("a@b.com", GOOD_PASSWORD)).role == "admin"

    async def test_the_email_is_normalised(self, users):
        await users.create(email="  A@B.CoM ", password=GOOD_PASSWORD)

        assert (await users.get_by_email("a@b.com")).email == "a@b.com"

    async def test_a_duplicate_email_is_rejected(self, users):
        await users.create(email="a@b.com", password=GOOD_PASSWORD)

        with pytest.raises(DuplicateUserError):
            await users.create(email="A@B.com", password=GOOD_PASSWORD)

    async def test_an_invalid_email_is_rejected(self, users):
        with pytest.raises(InvalidEmailError):
            await users.create(email="not-an-email", password=GOOD_PASSWORD)

    async def test_a_weak_password_never_reaches_storage(self, users):
        with pytest.raises(WeakPasswordError):
            await users.create(email="a@b.com", password="short")

        assert await users.count() == 0

    async def test_a_wrong_password_does_not_authenticate(self, users):
        await users.create(email="a@b.com", password=GOOD_PASSWORD)

        assert await users.authenticate("a@b.com", "wrong-password-x") is None

    async def test_an_unknown_account_does_not_authenticate(self, users):
        assert await users.authenticate("ghost@b.com", GOOD_PASSWORD) is None

    async def test_a_disabled_account_cannot_sign_in(self, users):
        await users.create(email="a@b.com", password=GOOD_PASSWORD)
        await users.set_active("a@b.com", False)

        assert await users.authenticate("a@b.com", GOOD_PASSWORD) is None

    async def test_the_last_admin_cannot_be_deleted(self, users):
        """An install with no administrator cannot be recovered via the API."""
        await users.create(email="a@b.com", password=GOOD_PASSWORD, role="admin")

        with pytest.raises(UserError, match="only active administrator"):
            await users.delete("a@b.com")

    async def test_an_admin_can_be_deleted_when_another_remains(self, users):
        await users.create(email="a@b.com", password=GOOD_PASSWORD, role="admin")
        await users.create(email="c@d.com", password=GOOD_PASSWORD, role="admin")

        await users.delete("a@b.com")

        assert await users.count() == 1


# ─── API ───


@pytest.fixture
async def client(tmp_path):
    database = Database(tmp_path / "api-auth.db")
    await database.connect()
    vault = CredentialVault(database, MASTER_KEY)
    settings = Settings(
        data_dir=tmp_path,
        secret_key=SECRET,
        network_policy="authorized-targets",
    )

    repo = UserRepository(database)
    await repo.create(email="admin@lynjax.test", password=GOOD_PASSWORD, role="admin")
    await repo.create(email="op@lynjax.test", password=GOOD_PASSWORD, role="operator")
    await repo.create(email="view@lynjax.test", password=GOOD_PASSWORD, role="viewer")

    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[get_vault] = lambda: vault
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    await database.disconnect()


def sign_in(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": GOOD_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class TestLogin:
    def test_valid_credentials_return_a_token(self, client):
        body = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@lynjax.test", "password": GOOD_PASSWORD},
        ).json()

        assert body["access_token"]
        assert body["role"] == "admin"

    def test_a_wrong_password_is_a_401(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@lynjax.test", "password": "wrong-password-x"},
        )

        assert response.status_code == 401

    def test_an_unknown_account_gives_the_same_message_as_a_wrong_password(
        self, client
    ):
        """Different messages would let anyone enumerate which addresses exist."""
        wrong = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@lynjax.test", "password": "wrong-password-x"},
        )
        missing = client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@lynjax.test", "password": GOOD_PASSWORD},
        )

        assert wrong.status_code == missing.status_code == 401
        assert wrong.json()["detail"] == missing.json()["detail"]

    def test_me_returns_the_signed_in_account(self, client):
        headers = sign_in(client, "op@lynjax.test")

        body = client.get("/api/v1/auth/me", headers=headers).json()

        assert body["email"] == "op@lynjax.test"
        assert body["role"] == "operator"


class TestRoleEnforcement:
    def test_a_viewer_can_read_the_inventory(self, client):
        headers = sign_in(client, "view@lynjax.test")

        assert client.get("/api/v1/devices", headers=headers).status_code == 200

    def test_a_viewer_cannot_register_a_device(self, client):
        headers = sign_in(client, "view@lynjax.test")

        response = client.post(
            "/api/v1/devices",
            headers=headers,
            json={"name": "sw", "host": "10.0.0.1", "connector_type": "ssh"},
        )

        assert response.status_code == 403
        assert "operator" in response.json()["detail"]

    def test_a_viewer_cannot_reach_the_network(self, client):
        """Touching a client's infrastructure is the action worth restricting."""
        headers = sign_in(client, "view@lynjax.test")

        for path in ("/api/v1/audit", "/api/v1/trace/10.0.0.1"):
            assert client.post(path, headers=headers, json={}).status_code == 403

    def test_an_operator_can_run_an_audit(self, client):
        headers = sign_in(client, "op@lynjax.test")

        assert client.post("/api/v1/audit", headers=headers, json={}).status_code == 200

    def test_an_operator_cannot_manage_accounts(self, client):
        headers = sign_in(client, "op@lynjax.test")

        assert client.get("/api/v1/auth/users", headers=headers).status_code == 403

    def test_an_admin_can_manage_accounts(self, client):
        headers = sign_in(client, "admin@lynjax.test")

        assert client.get("/api/v1/auth/users", headers=headers).status_code == 200

    def test_an_admin_cannot_delete_their_own_account(self, client):
        headers = sign_in(client, "admin@lynjax.test")

        response = client.delete(
            "/api/v1/auth/users/admin@lynjax.test", headers=headers
        )

        assert response.status_code == 409


class TestTokenHandling:
    def test_a_request_without_a_token_is_refused_with_instructions(self, client):
        response = client.get("/api/v1/devices")

        assert response.status_code == 401
        assert "auth/login" in response.json()["detail"]

    def test_a_forged_token_is_refused(self, client):
        forged = create_access_token(
            subject="admin@lynjax.test",
            role="admin",
            secret="another-secret-long-enough-for-hs256-warnings",
        )

        response = client.get(
            "/api/v1/devices", headers={"Authorization": f"Bearer {forged}"}
        )

        assert response.status_code == 401

    def test_a_token_for_a_deleted_account_stops_working(self, client):
        """The user is re-read per request; a valid signature is not enough."""
        headers = sign_in(client, "view@lynjax.test")
        admin = sign_in(client, "admin@lynjax.test")
        client.delete("/api/v1/auth/users/view@lynjax.test", headers=admin)

        assert client.get("/api/v1/devices", headers=headers).status_code == 401

    def test_a_demoted_account_loses_access_immediately(self, client):
        """A token stays valid for hours, so a demotion cannot wait for expiry.
        The user is re-read from the database on every request, which is what
        makes that possible."""
        headers = sign_in(client, "op@lynjax.test")
        assert client.post("/api/v1/audit", headers=headers, json={}).status_code == 200

        admin = sign_in(client, "admin@lynjax.test")
        # Demote by recreating the account through the admin API, which is the
        # path an administrator actually has.
        client.delete("/api/v1/auth/users/op@lynjax.test", headers=admin)
        client.post(
            "/api/v1/auth/users",
            headers=admin,
            json={
                "email": "op@lynjax.test",
                "password": GOOD_PASSWORD,
                "role": "viewer",
            },
        )

        # The old token names an account that exists again but is now a viewer.
        assert client.post("/api/v1/audit", headers=headers, json={}).status_code == 403


class TestEveryRouteIsProtected:
    """The sweep: no API route may answer without a token.

    Guards applied endpoint by endpoint get forgotten on the next endpoint. This
    walks the router instead, so a new unprotected route fails the suite.
    """

    #: Endpoints that are unauthenticated by design.
    PUBLIC = {
        ("POST", "/api/v1/auth/login"),
        ("GET", "/api/v1/info"),
        # The connectivity demo opens no sockets and touches no stored data.
        ("POST", "/api/v1/assessments/connectivity-demo"),
    }

    def test_no_api_route_answers_without_a_token(self, client):
        unprotected: list[str] = []

        for route in app.routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set())
            if not path.startswith("/api/v1"):
                continue

            for method in sorted(methods - {"HEAD", "OPTIONS"}):
                if (method, path) in self.PUBLIC:
                    continue

                # Fill path parameters with something harmless.
                url = path.replace("{device_id}", "1").replace("{job_id}", "x")
                url = url.replace("{assessment_id}", "x").replace(
                    "{target_ip}", "10.0.0.1"
                )
                url = url.replace("{email}", "someone@example.com")

                response = client.request(method, url, json={})
                if response.status_code not in (401, 403):
                    unprotected.append(f"{method} {path} -> {response.status_code}")

        assert unprotected == [], (
            "These routes answered without authentication: " + ", ".join(unprotected)
        )
