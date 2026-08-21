#!/usr/bin/env python3
"""didox — CLI for the Didox.uz EDO partner API, built for AI agents and humans.

Zero dependencies: Python 3.8+ stdlib only.

Configuration (env vars or an env file):
  DIDOX_PARTNER_TOKEN   partner JWT (required)
  DIDOX_TIN             company TIN, e.g. 313022075 (required)
  DIDOX_URL             API base, default https://api-partners.didox.uz
  DIDOX_PASSWORD        Didox account password (only for `login`)
  DIDOX_STATE_DIR       where to keep the cached user token, default ~/.didox

Env file lookup order: --env PATH, ./.env, ~/.didox/env

Usage:
  didox.py login                          # get user token via account password
  didox.py profile                        # who am I
  didox.py docs [--owner 0|1] [--status N] [--partner TIN] [--doctype T]
                [--page N] [--limit N]    # list documents
  didox.py doc DOC_ID                     # document details (JSON)
  didox.py doc-pdf DOC_ID OUT.pdf         # download print form
  didox.py stats                          # document counters
  didox.py partner TIN                    # company info by TIN
  didox.py draft-delete DOC_ID            # delete a draft
  didox.py raw METHOD PATH [JSON_BODY]    # escape hatch: raw API call

All output is JSON on stdout. Errors go to stderr with exit code 1.
Signing is NOT implemented here on purpose: it requires the E-IMZO key.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://api-partners.didox.uz"
TOKEN_TTL_SECONDS = 355 * 60  # server issues 360 min; refresh slightly early


def load_env(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    candidates.append(Path.cwd() / ".env")
    candidates.append(Path.home() / ".didox" / "env")
    for path in candidates:
        if path.is_file():
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
            break


def require_env(name):
    value = os.environ.get(name)
    if not value:
        fail(f"missing {name}: set it in the environment or an env file (see --help)")
    return value


def state_dir():
    directory = Path(os.environ.get("DIDOX_STATE_DIR", Path.home() / ".didox"))
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory


def token_cache_path():
    tin = require_env("DIDOX_TIN")
    host = urllib.parse.urlparse(os.environ.get("DIDOX_URL", DEFAULT_URL)).netloc
    return state_dir() / f"token-{host}-{tin}.json"


def fail(message):
    print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


def api_request(method, path, body=None, user_key=None, raw_response=False):
    base = os.environ.get("DIDOX_URL", DEFAULT_URL).rstrip("/")
    url = base + path
    headers = {
        "Partner-Authorization": require_env("DIDOX_PARTNER_TOKEN"),
        "Accept": "application/json",
    }
    if user_key:
        headers["user-key"] = user_key
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        fail(f"HTTP {error.code} {method} {path}: {detail[:500]}")
    except urllib.error.URLError as error:
        fail(f"network error for {method} {path}: {error.reason}")
    if raw_response:
        return payload
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {"raw": payload.decode(errors="replace")}


def get_user_key(force_login=False):
    cache = token_cache_path()
    if not force_login and cache.is_file():
        try:
            entry = json.loads(cache.read_text())
            if time.time() - entry["issued_at"] < TOKEN_TTL_SECONDS:
                return entry["token"]
        except (KeyError, json.JSONDecodeError):
            pass
    password = os.environ.get("DIDOX_PASSWORD")
    if not password:
        fail(
            "no valid user token cached and DIDOX_PASSWORD is not set; "
            "run `didox.py login` on a machine where DIDOX_PASSWORD is configured"
        )
    tin = require_env("DIDOX_TIN")
    result = api_request("POST", f"/v1/auth/{tin}/password/ru", {"password": password})
    token = (result or {}).get("token") or (result or {}).get("data", {}).get("token")
    if not token:
        fail(f"login succeeded but no token in response: {json.dumps(result)[:300]}")
    cache.write_text(json.dumps({"token": token, "issued_at": time.time()}))
    cache.chmod(0o600)
    return token


def emit(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_login(_args):
    token = get_user_key(force_login=True)
    emit({"ok": True, "token_cached": str(token_cache_path()), "ttl_minutes": 360,
          "token_preview": token[:8] + "..."})


def cmd_profile(_args):
    emit(api_request("GET", "/v1/profile", user_key=get_user_key()))


def cmd_docs(args):
    params = {"page": args.page, "limit": args.limit, "owner": args.owner}
    if args.status:
        params["status"] = args.status
    if args.partner:
        params["partner"] = args.partner
    if args.doctype:
        params["doctype"] = args.doctype
    query = urllib.parse.urlencode(params)
    emit(api_request("GET", f"/v2/documents?{query}", user_key=get_user_key()))


def cmd_doc(args):
    emit(api_request("GET", f"/v1/documents/{args.doc_id}", user_key=get_user_key()))


def cmd_doc_pdf(args):
    payload = api_request(
        "GET", f"/v1/documents/view/{args.doc_id}/pdf/ru",
        user_key=get_user_key(), raw_response=True,
    )
    out = Path(args.output)
    out.write_bytes(payload)
    emit({"ok": True, "file": str(out), "bytes": len(payload)})


def cmd_stats(args):
    # The API counts INCOMING docs when owner is omitted (opposite of the list
    # endpoint's default), so always pass owner explicitly to stay consistent.
    params = {"owner": args.owner}
    if args.partner:
        params["partner"] = args.partner
    if args.doctype:
        params["doctype"] = args.doctype
    query = urllib.parse.urlencode(params)
    emit(api_request("GET", f"/v2/documents/statistics/all?{query}",
                     user_key=get_user_key()))


def cmd_partner(args):
    emit(api_request("GET", f"/v1/utils/info/{args.tin}", user_key=get_user_key()))


def cmd_draft_000(args):
    import base64

    user_key = get_user_key()
    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        fail(f"PDF not found: {pdf_path}")
    if pdf_path.stat().st_size > 10 * 1024 * 1024:
        fail("PDF is over the 10 MB Didox limit")

    seller = api_request("GET", "/v1/profile", user_key=user_key)
    buyer = api_request("GET", f"/v1/utils/info/{args.buyer_tin}", user_key=user_key)
    buyer_name = buyer.get("shortName") or buyer.get("name")
    buyer_address = (buyer.get("address") or buyer.get("fullAddress") or "").strip()
    if not buyer_name:
        fail(f"could not resolve buyer {args.buyer_tin}: {json.dumps(buyer)[:300]}")

    payload = {
        "data": {
            "Document": {
                "DocumentNo": args.number,
                "DocumentDate": args.date,
            },
            "Subtype": args.subtype,
            "SellerTin": seller["tin"],
            "Seller": {
                "Name": seller["shortName"],
                "BranchCode": "",
                "BranchName": "",
                "Address": (seller.get("address") or "").strip(),
            },
            "BuyerTin": args.buyer_tin,
            "Buyer": {
                "Name": buyer_name,
                "BranchCode": "",
                "BranchName": "",
                "Address": buyer_address,
            },
        },
        "document": "data:application/pdf;base64,"
        + base64.b64encode(pdf_path.read_bytes()).decode(),
    }
    if args.name:
        payload["data"]["Document"]["DocumentName"] = args.name
    if args.contract_no:
        payload["data"]["ContractDoc"] = {
            "ContractNo": args.contract_no,
            "ContractDate": args.contract_date or args.date,
        }
    emit(api_request("POST", "/v1/documents/000/create", body=payload,
                     user_key=user_key))


def cmd_draft_delete(args):
    emit(api_request("POST", f"/v1/documents/{args.doc_id}/delete/draft",
                     user_key=get_user_key()))


def make_signature(data_b64, serial, user_key):
    """PKCS7 via local E-IMZO bridge + timestamp via Didox. Returns timeStampTokenB64."""
    import subprocess

    bridge = Path(__file__).with_name("eimzo_sign.py")
    proc = subprocess.run(
        ["uv", "run", str(bridge), "sign", data_b64, "--serial", serial],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        fail(f"E-IMZO signing failed: {proc.stderr.strip()[:400]}")
    signed = json.loads(proc.stdout)
    stamped = api_request(
        "POST", "/v1/dsvs/timestamp",
        body={"pkcs7": signed["pkcs7_64"], "signatureHex": signed["signature_hex"]},
        user_key=user_key,
    )
    token = (stamped or {}).get("timeStampTokenB64")
    if not token:
        fail(f"timestamp not attached: {json.dumps(stamped)[:300]}")
    return token


def sign_json_object(obj, serial, user_key):
    import base64

    data_b64 = base64.b64encode(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
    ).decode()
    return make_signature(data_b64, serial, user_key)


def gate_submit(args, action, payload_note):
    if not args.submit:
        emit({"ok": True, "prepared": action, "submitted": False,
              "note": f"{payload_note}; re-run with --submit to send"})
        sys.exit(0)


def cmd_sign(args):
    user_key = get_user_key()
    doc = api_request("GET", f"/v1/documents/{args.doc_id}?owner=1", user_key=user_key)
    to_sign = (doc or {}).get("data", {}).get("json")
    if to_sign is None:
        fail(f"document {args.doc_id} has no data.json to sign "
             f"(already signed, or not an outgoing draft): {json.dumps(doc)[:300]}")
    token = sign_json_object(to_sign, args.serial, user_key)
    gate_submit(args, "sign", "signature + timestamp ready")
    result = api_request("POST", f"/v1/documents/{args.doc_id}/sign",
                         body={"signature": token}, user_key=user_key)
    emit({"ok": True, "submitted": True, "result": result})


def cmd_accept(args):
    """Sign an INCOMING document: documentBase64 sig + toSign sig, joined."""
    user_key = get_user_key()
    doc_b64 = api_request("GET", f"/v1/documents/{args.doc_id}/documentBase64",
                          user_key=user_key)
    payload = doc_b64 if isinstance(doc_b64, str) else (
        doc_b64.get("data") or doc_b64.get("documentBase64"))
    if not payload:
        fail(f"no documentBase64 for {args.doc_id}: {json.dumps(doc_b64)[:200]}")
    my_signature = make_signature(payload, args.serial, user_key)

    doc = api_request("GET", f"/v1/documents/{args.doc_id}?owner=0", user_key=user_key)
    to_sign = (doc or {}).get("data", {}).get("toSign")
    if not to_sign:
        fail(f"document {args.doc_id} has no toSign data (nothing awaits your signature)")
    joined = api_request("POST", "/v1/dsvs/signature/join",
                         body={"signature1": to_sign, "signature2": my_signature},
                         user_key=user_key)
    pkcs7 = (joined or {}).get("pkcs7B64")
    if not pkcs7:
        fail(f"signature join failed: {json.dumps(joined)[:300]}")
    gate_submit(args, "accept", "joined signature ready")
    result = api_request("POST", f"/v1/documents/{args.doc_id}/sign",
                         body={"signature": pkcs7}, user_key=user_key)
    emit({"ok": True, "submitted": True, "result": result})


def cmd_reject(args):
    user_key = get_user_key()
    data = api_request("POST", f"/v1/documents/{args.doc_id}/tosign",
                       body={"action": "reject", "comment": args.comment},
                       user_key=user_key)
    obj = (data or {}).get("data")
    if not obj:
        fail(f"tosign returned no data: {json.dumps(data)[:300]}")
    token = sign_json_object(obj, args.serial, user_key)
    gate_submit(args, "reject", "rejection signature ready")
    result = api_request("POST", f"/v1/documents/{args.doc_id}/reject",
                         body={"signature": token, "comment": args.comment},
                         user_key=user_key)
    emit({"ok": True, "submitted": True, "result": result})


def cmd_cancel(args):
    user_key = get_user_key()
    data = api_request("POST", f"/v1/documents/{args.doc_id}/tosign",
                       body={"action": "cancel"}, user_key=user_key)
    obj = (data or {}).get("data")
    if not obj:
        fail(f"tosign returned no data: {json.dumps(data)[:300]}")
    token = sign_json_object(obj, args.serial, user_key)
    gate_submit(args, "cancel", "cancellation signature ready")
    result = api_request("POST", f"/v1/documents/{args.doc_id}/delete",
                         body={"signature": token}, user_key=user_key)
    emit({"ok": True, "submitted": True, "result": result})


def cmd_create(args):
    payload = json.loads(Path(args.json_file).read_text())
    emit(api_request("POST", f"/v1/documents/{args.doctype}/create/ru",
                     body=payload, user_key=get_user_key()))


def cmd_draft_update(args):
    payload = json.loads(Path(args.json_file).read_text())
    emit(api_request("POST", f"/v1/documents/{args.doc_id}/update/{args.doctype}/ru",
                     body=payload, user_key=get_user_key()))


def cmd_raw(args):
    body = json.loads(args.body) if args.body else None
    emit(api_request(args.method.upper(), args.path, body=body,
                     user_key=get_user_key()))


def main():
    parser = argparse.ArgumentParser(
        prog="didox.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--env", help="path to env file")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login").set_defaults(func=cmd_login)
    sub.add_parser("profile").set_defaults(func=cmd_profile)

    docs = sub.add_parser("docs")
    docs.add_argument("--owner", default="1", choices=["0", "1"],
                      help="1=outgoing (default), 0=incoming")
    docs.add_argument("--status", help="document status code")
    docs.add_argument("--partner", help="filter by partner TIN")
    docs.add_argument("--doctype", help="doc type code, e.g. 000,002,005")
    docs.add_argument("--page", type=int, default=1)
    docs.add_argument("--limit", type=int, default=20)
    docs.set_defaults(func=cmd_docs)

    doc = sub.add_parser("doc")
    doc.add_argument("doc_id")
    doc.set_defaults(func=cmd_doc)

    doc_pdf = sub.add_parser("doc-pdf")
    doc_pdf.add_argument("doc_id")
    doc_pdf.add_argument("output")
    doc_pdf.set_defaults(func=cmd_doc_pdf)

    stats = sub.add_parser("stats")
    stats.add_argument("--owner", default="1", choices=["0", "1"],
                       help="1=outgoing (default, same as docs), 0=incoming")
    stats.add_argument("--partner", help="filter by partner TIN")
    stats.add_argument("--doctype", help="doc type code")
    stats.set_defaults(func=cmd_stats)

    partner = sub.add_parser("partner")
    partner.add_argument("tin")
    partner.set_defaults(func=cmd_partner)

    draft = sub.add_parser("draft-000", help="create arbitrary-document draft with a PDF")
    draft.add_argument("--number", required=True, help="document number")
    draft.add_argument("--date", required=True, help="document date YYYY-MM-DD")
    draft.add_argument("--buyer-tin", required=True, help="partner TIN")
    draft.add_argument("--pdf", required=True, help="path to PDF file (<=10MB)")
    draft.add_argument("--subtype", type=int, required=True,
                       help="5=act of completed works, 6=other, ... (see skill)")
    draft.add_argument("--name", help="document title")
    draft.add_argument("--contract-no", help="contract number")
    draft.add_argument("--contract-date", help="contract date YYYY-MM-DD")
    draft.set_defaults(func=cmd_draft_000)

    draft_delete = sub.add_parser("draft-delete")
    draft_delete.add_argument("doc_id")
    draft_delete.set_defaults(func=cmd_draft_delete)

    def signing_parser(name, help_text, needs_comment=False):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("doc_id")
        p.add_argument("--serial", required=True,
                       help="ЭЦП key serial (from eimzo_sign.py keys)")
        p.add_argument("--submit", action="store_true",
                       help="actually send (default: prepare signature only)")
        if needs_comment:
            p.add_argument("--comment", required=True, help="reason, goes to the partner")
        return p

    signing_parser("sign", "sign an OUTGOING document via local E-IMZO").set_defaults(func=cmd_sign)
    signing_parser("accept", "sign/accept an INCOMING document").set_defaults(func=cmd_accept)
    signing_parser("reject", "reject an incoming document", needs_comment=True).set_defaults(func=cmd_reject)
    signing_parser("cancel", "cancel a SENT outgoing document").set_defaults(func=cmd_cancel)

    create = sub.add_parser("create", help="create a draft of any doctype from a JSON file")
    create.add_argument("doctype", help="002, 005, 007, 000, 052, ... (see references)")
    create.add_argument("json_file", help="payload per references/document-types.md")
    create.set_defaults(func=cmd_create)

    draft_update = sub.add_parser("draft-update", help="update an existing draft")
    draft_update.add_argument("doc_id")
    draft_update.add_argument("doctype")
    draft_update.add_argument("json_file")
    draft_update.set_defaults(func=cmd_draft_update)

    raw = sub.add_parser("raw")
    raw.add_argument("method")
    raw.add_argument("path")
    raw.add_argument("body", nargs="?")
    raw.set_defaults(func=cmd_raw)

    args = parser.parse_args()
    load_env(args.env)
    args.func(args)


if __name__ == "__main__":
    main()
