SESSION_HEADER = "X-Session-Id"


def session_id_from_request(request):
    """Opaque per-browser session id from the X-Session-Id header (or "" if
    absent). Scopes documents and retrieval to a single visitor — this is a
    lightweight demo isolation boundary, not authentication.
    """
    return request.headers.get(SESSION_HEADER, "").strip()