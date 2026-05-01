# User Service — API Documentation

Base URL: `https://<host>/api`

All request and response bodies are JSON. Timestamps are UTC ISO 8601.

---

## Authentication

Protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <accessToken>
```

Endpoints marked **`[ADMIN]`** additionally require the `ADMIN` role encoded in the token's claims.

---

## Common Response Shapes

### `AuthResponse`
Returned on successful login and token refresh.

```json
{
  "publicId": "uuid",
  "chainId": "uuid",
  "accessToken": "string",
  "refreshToken": "string",
  "accessTokenExpiresAt": "2026-04-28T10:15:00Z",
  "refreshTokenExpiresAt": "2026-05-05T10:00:00Z"
}
```

| Field | Description |
|-------|-------------|
| `publicId` | Public-facing user identifier. Use this to reference users externally. |
| `chainId` | Login session identifier. All refresh tokens issued from one login share the same chain. |
| `accessToken` | Short-lived JWT (15 min). |
| `refreshToken` | Opaque random token. Store securely and use to obtain a new access token. |

### `AuthUserDto`
Returned after successful registration confirmation.

```json
{
  "publicId": "uuid",
  "email": "user@example.com",
  "name": "John",
  "surname": "Doe",
  "age": 25,
  "gender": "male",
  "isVerified": true,
  "dateJoined": "2026-04-28T10:00:00Z",
  "roles": ["USER"]
}
```

### `UserProfileDto`
Returned from user self-service profile endpoints.

```json
{
  "publicId": "uuid",
  "email": "user@example.com",
  "name": "John",
  "surname": "Doe",
  "age": 25,
  "gender": "male",
  "isVerified": true,
  "dateJoined": "2026-04-28T10:00:00Z",
  "dateDeleted": null,
  "isDeleted": false,
  "roles": ["USER"]
}
```

### `RegistrationResponse`
Returned when a registration or code resend is initiated.

```json
{
  "email": "user@example.com",
  "verificationCodeExpiresAt": "2026-04-28T10:15:00Z",
  "message": "Verification code sent. Confirm registration to create the account."
}
```

---

## Auth Endpoints — `/api/auth`

### `POST /api/auth/register`

Starts the registration flow. Validates input, stores a pending registration, and emails a 6-digit code to the provided address. If a pending registration for that email already exists, it is overwritten with fresh data and a new code.

**Auth:** None

**Request body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `email` | string | Valid email format, trimmed and lowercased |
| `password` | string | Any non-empty string |

> Profile fields (`name`, `surname`, `age`, `gender`) are not collected at registration. The account is created with empty name/surname, `age = 0`, and `gender = "unknown"`. Use `PUT /api/user/me` after login to populate them.

**Responses:**

| Status | Meaning |
|--------|---------|
| `202 Accepted` | Pending registration created; code emailed. Body: `RegistrationResponse`. |
| `409 Conflict` | A verified account with this email already exists. Body: `{ "message": "Email already exists." }` |

---

### `POST /api/auth/register/resend-code`

Resends the verification code to an existing pending registration.

**Auth:** None

**Request body:**

```json
{
  "email": "user@example.com"
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | New code emailed. Body: `RegistrationResponse`. |
| `404 Not Found` | No pending registration for this email. |
| `409 Conflict` | A verified account with this email already exists. |

---

### `POST /api/auth/register/confirm`

Completes registration. Validates the 6-digit code, creates the `User` record with the `USER` role, and deletes the pending registration.

**Auth:** None

**Request body:**

```json
{
  "email": "user@example.com",
  "code": "482910"
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | Account created. Body: `AuthUserDto`. |
| `400 Bad Request` | Code is invalid or expired. Body: `{ "message": "Invalid or expired verification code." }` |
| `409 Conflict` | A verified account with this email already exists (race condition guard). |

---

### `POST /api/auth/login`

Authenticates the user and issues an access token + refresh token pair. A new refresh token chain is created per login. On login, a verification code is also queued for the user's email.

**Auth:** None

**Request body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "rememberMe": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `rememberMe` | bool | `false` → refresh token expires in 7 days. `true` → 30 days. |

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | Body: `AuthResponse`. |
| `401 Unauthorized` | Invalid credentials or soft-deleted account. Body: `{ "message": "Invalid credentials or inactive account." }` |

---

### `POST /api/auth/refresh`

Rotates the refresh token. The submitted token is revoked and a new access + refresh token pair is issued under the same chain.

**Auth:** None

**Request body:**

```json
{
  "refreshToken": "<raw-refresh-token>"
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | Body: `AuthResponse` with new tokens. |
| `401 Unauthorized` | Token not found, already revoked, expired, or user is deleted. Body: `{ "message": "Invalid refresh token." }` |

---

### `POST /api/auth/logout`

Revokes a single refresh token for the authenticated user.

**Auth:** Bearer token required

**Request body:**

```json
{
  "refreshToken": "<raw-refresh-token>"
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Token revoked. |
| `401 Unauthorized` | Missing or invalid access token. |
| `404 Not Found` | Refresh token not found. |

---

### `POST /api/auth/logout-all`

Revokes all refresh tokens for the authenticated user (all devices/sessions).

**Auth:** Bearer token required

**Request body:** None

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | All tokens revoked. |
| `401 Unauthorized` | Missing or invalid access token. |
| `404 Not Found` | User not found. |

---

### `POST /api/auth/resend-email-code`

Sends a new email verification code to the given address. Used when a user needs to verify their email after login but has not yet done so.

**Auth:** None

**Request body:**

```json
{
  "email": "user@example.com",
  "code": ""
}
```

> Note: `code` is part of `VerifyEmailRequest` but is ignored here — only `email` is used. Send an empty string or any value.

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Code emailed. |
| `404 Not Found` | No user with this email. |

---

### `POST /api/auth/verify-email`

Marks the user's email as verified after confirming the code.

**Auth:** None

**Request body:**

```json
{
  "email": "user@example.com",
  "code": "482910"
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Email verified. |
| `400 Bad Request` | Code invalid or expired. Body: `{ "message": "Invalid or expired verification code." }` |

---

## User Endpoints — `/api/user`

All endpoints in this group require a valid Bearer token.

---

### `GET /api/user/me`

Returns the authenticated user's profile.

**Auth:** Bearer token required

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | Body: `UserProfileDto`. |
| `401 Unauthorized` | Missing or invalid token. |
| `404 Not Found` | User not found. |

---

### `PUT /api/user/me`

Updates the authenticated user's profile.

**Auth:** Bearer token required

**Request body:**

```json
{
  "name": "John",
  "surname": "Doe",
  "age": 26,
  "gender": "male"
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `name` | string | Required, trimmed |
| `surname` | string | Required, trimmed |
| `age` | int | 0–120 |
| `gender` | string | One of: `male`, `female`, `other`, `unknown`, `prefer_not_to_say` |

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | Body: updated `UserProfileDto`. |
| `401 Unauthorized` | Missing or invalid token. |
| `404 Not Found` | User not found. |

---

### `POST /api/user/me/email/resend-code`

Requests a verification code for changing the email address. The code is sent to the *new* email address.

**Auth:** Bearer token required

**Request body:**

```json
{
  "newEmail": "newemail@example.com"
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Code sent to the new email. |
| `401 Unauthorized` | Missing or invalid token. |
| `404 Not Found` | User not found. |
| `409 Conflict` | New email is already in use by another account. |

---

### `POST /api/user/me/email/confirm`

Confirms the email change using the code sent to the new address. Updates the email and marks the account as verified.

**Auth:** Bearer token required

**Request body:**

```json
{
  "newEmail": "newemail@example.com",
  "code": "193847"
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Email updated and account re-verified. |
| `400 Bad Request` | Code invalid or expired. Body: `{ "message": "Invalid or expired verification code." }` |
| `401 Unauthorized` | Missing or invalid token. |
| `409 Conflict` | New email is already in use. |

---

### `POST /api/user/me/password/resend-code`

Initiates a password change. Verifies the current password and sends a 6-digit code to the user's current email.

**Auth:** Bearer token required

**Request body:**

```json
{
  "currentPassword": "OldPass123"
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Code sent to current email. |
| `400 Bad Request` | Current password is wrong or user not found. |
| `401 Unauthorized` | Missing or invalid token. |

---

### `POST /api/user/me/password/confirm`

Completes the password change using the code sent in the previous step.

**Auth:** Bearer token required

**Request body:**

```json
{
  "code": "382910",
  "newPassword": "NewSecurePass456"
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Password updated. |
| `400 Bad Request` | Code invalid or expired. Body: `{ "message": "Invalid or expired verification code." }` |
| `401 Unauthorized` | Missing or invalid token. |

---

## Admin Endpoints — `/api/admin`

All endpoints in this group require a Bearer token with the `ADMIN` role.

### `AdminUserDto` shape

```json
{
  "id": "uuid",
  "publicId": "uuid",
  "email": "user@example.com",
  "name": "John",
  "surname": "Doe",
  "age": 25,
  "gender": "male",
  "isVerified": true,
  "dateJoined": "2026-04-28T10:00:00Z",
  "dateDeleted": null,
  "isDeleted": false,
  "roles": ["USER"]
}
```

> `id` is the internal database GUID. `publicId` is the externally exposed identifier.

---

### `GET /api/admin/users`

Returns all users (including soft-deleted — see note below).

**Auth:** `[ADMIN]`

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | Body: array of `AdminUserDto`. |

> Note: EF Core global query filters exclude soft-deleted records by default. The admin list therefore returns only non-deleted users unless the service layer explicitly bypasses the filter.

---

### `GET /api/admin/users/{id}`

Returns a single user by internal GUID.

**Auth:** `[ADMIN]`

**Path params:**

| Param | Type | Description |
|-------|------|-------------|
| `id` | guid | Internal user ID (`AdminUserDto.id`) |

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | Body: `AdminUserDto`. |
| `404 Not Found` | User not found. |

---

### `POST /api/admin/users`

Creates a user directly, bypassing the email verification flow. Assigns the `USER` role automatically and queues an email verification code.

**Auth:** `[ADMIN]`

**Request body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "name": "John",
  "surname": "Doe",
  "age": 25,
  "gender": "male",
  "isVerified": false,
  "dateJoined": null,
  "dateDeleted": null,
  "isDeleted": false
}
```

| Field | Type | Notes |
|-------|------|-------|
| `isVerified` | bool | Defaults to `false` if omitted |
| `dateJoined` | datetime? | Defaults to `UtcNow` if null |
| `dateDeleted` | datetime? | Optional |
| `isDeleted` | bool | Soft-delete flag |

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | Body: `AdminUserDto`. |
| `409 Conflict` | Email already exists. |

---

### `PUT /api/admin/users/{id}`

Partially updates a user. Only fields that are non-null / non-empty are applied. If `email` changes, `isVerified` is reset to `false` and a new verification code is emailed.

**Auth:** `[ADMIN]`

**Path params:** `id` — internal user GUID

**Request body** (all fields optional):

```json
{
  "email": "new@example.com",
  "password": "NewPass123",
  "name": "Jane",
  "surname": "Smith",
  "age": 30,
  "gender": "female",
  "isVerified": true,
  "dateJoined": "2026-01-01T00:00:00Z",
  "dateDeleted": null,
  "isDeleted": false
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | Body: updated `AdminUserDto`. |
| `404 Not Found` | User not found. |
| `409 Conflict` | New email is already taken. |

---

### `DELETE /api/admin/users/{id}`

Soft-deletes a user (sets `isDeleted = true`, `dateDeleted = UtcNow`).

**Auth:** `[ADMIN]`

**Path params:** `id` — internal user GUID

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | User soft-deleted. |
| `404 Not Found` | User not found. |

---

### `GET /api/admin/roles`

Returns all available roles.

**Auth:** `[ADMIN]`

**Response body:**

```json
[
  { "id": "5e8e5f7a-0ba9-44d9-a9cc-b2c34d1821aa", "name": "USER", "description": "Default user role" },
  { "id": "67d786a4-86fa-4e8e-b038-451c0b06f0f0", "name": "ADMIN", "description": "Administrator role" },
  { "id": "5a17334f-7431-4256-859a-9b2251ef7e22", "name": "PREMIUMUSER", "description": "Premium user role" }
]
```

---

### `POST /api/admin/users/{id}/roles`

Adds roles to a user without removing existing ones. If a role link was previously soft-deleted, it is restored.

**Auth:** `[ADMIN]`

**Path params:** `id` — internal user GUID

**Request body:**

```json
{
  "roleIds": [
    "5a17334f-7431-4256-859a-9b2251ef7e22"
  ]
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Roles added. |
| `404 Not Found` | User not found. |

> Unknown `roleIds` are silently skipped.

---

### `PUT /api/admin/users/{id}/roles`

Replaces the user's entire role set. Roles in the request are activated; all others are soft-deleted.

**Auth:** `[ADMIN]`

**Path params:** `id` — internal user GUID

**Request body:**

```json
{
  "roleIds": [
    "5e8e5f7a-0ba9-44d9-a9cc-b2c34d1821aa",
    "5a17334f-7431-4256-859a-9b2251ef7e22"
  ]
}
```

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Role set replaced. |
| `404 Not Found` | User not found. |

---

### `DELETE /api/admin/users/{id}/roles/{roleId}`

Removes a single role from a user (soft-delete).

**Auth:** `[ADMIN]`

**Path params:**

| Param | Type |
|-------|------|
| `id` | guid — internal user GUID |
| `roleId` | guid — role GUID from `GET /api/admin/roles` |

**Responses:**

| Status | Meaning |
|--------|---------|
| `204 No Content` | Role removed. |
| `404 Not Found` | User–role link not found or already removed. |

---

## Internal Endpoints — `/api/internal/users`

Intended for service-to-service communication within the backend.

---

### `GET /api/internal/users/{id}`

Returns a raw user object by internal GUID.

**Auth:** `[ADMIN]`

**Path params:** `id` — internal user GUID

**Responses:**

| Status | Meaning |
|--------|---------|
| `200 OK` | Body: user object. |
| `404 Not Found` | User not found. |

---

### `POST /api/internal/users/validate-token`

Checks whether a given string is a structurally valid JWT. Does **not** verify signature or expiry — use this only as a quick format check.

**Auth:** None

**Request body:**

```json
{
  "token": "<jwt-string>"
}
```

**Response:**

```json
{
  "valid": true
}
```

| Status | Meaning |
|--------|---------|
| `200 OK` | Always returned. `valid` is `true` if the token can be parsed as a JWT, `false` otherwise. |

---

## Validation Rules Summary

| Field | Rule |
|-------|------|
| `email` | Must be valid RFC format; normalized to lowercase |
| `age` | Integer, 0–120 inclusive |
| `gender` | One of: `male`, `female`, `other`, `unknown`, `prefer_not_to_say` (case-insensitive) |
| Verification codes | 6-digit string, expire after **15 minutes**. Consuming a code deletes all codes of the same purpose for that user. |
| Access token lifetime | **15 minutes** |
| Refresh token lifetime | **7 days** (or **30 days** with `rememberMe: true`) |
