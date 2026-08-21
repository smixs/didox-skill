# /// script
# requires-python = ">=3.10"
# dependencies = ["websockets>=12"]
# ///
"""eimzo_sign — bridge to the local E-IMZO agent (CAPIWS websocket).

Talks to the E-IMZO desktop app on ws://127.0.0.1:64646 and creates PKCS7
signatures with a PFX key. The key password is entered by the USER in the
E-IMZO window (E-IMZO may cache it ~6 hours) — this script never sees, stores
or transmits the password.

Quirk handled here: the E-IMZO agent closes the websocket after EACH message,
so every call opens its own short-lived connection.

Usage:
  uv run eimzo_sign.py keys                       # list PFX keys (tin, serial, validto)
  uv run eimzo_sign.py sign <data_base64> --serial <cert_serial>
                                                  # create PKCS7 over the base64 data

Output: JSON on stdout. Errors: JSON on stderr, exit 1. E-IMZO app must run.
"""

import argparse
import asyncio
import json
import re
import sys

import websockets

WS_URL = "ws://127.0.0.1:64646/service/cryptapi"
ORIGIN = "http://localhost"
# Public localhost API keys shipped by E-IMZO (official docs, qo0p/e-imzo-doc).
LOCALHOST_API_KEYS = [
    "localhost",
    "96D0C1491615C82B9A54D9989779DF825B690748224C2B04F500F370D51827CE"
    "2644D8D4A82C18184D73AB8530BB8ED537269603F61DB0D03D2104ABF789970B",
    "127.0.0.1",
    "A7BCFA5D490B351BE0754130DF03A068F855DB4333D43921125B9CF2670EF6A4"
    "0370C646B90401955E1F7BC9CDBF59CE0B2C5467D820BE189C845D0B79CFC96F",
]


def fail(message):
    print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


async def call(payload, timeout=180):
    """Open a fresh connection, send one message, return the parsed reply.

    E-IMZO closes the socket after each message, so reusing a connection fails.
    """
    try:
        async with websockets.connect(
            WS_URL, origin=ORIGIN, max_size=50 * 1024 * 1024
        ) as ws:
            await ws.send(json.dumps(payload))
            response = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
    except OSError:
        fail("cannot reach E-IMZO on 127.0.0.1:64646 — is the E-IMZO app running?")
    if not response.get("success", False):
        fail(f"E-IMZO error for {payload.get('name')}: "
             f"{response.get('reason', json.dumps(response)[:300])}")
    return response


async def apikey():
    await call({"name": "apikey", "arguments": LOCALHOST_API_KEYS})


def parse_alias(alias):
    def field(pattern):
        match = re.search(pattern, alias)
        return match.group(1) if match else None
    return {
        "tin": field(r"1\.2\.860\.3\.16\.1\.2=(\d+)"),
        "serial": field(r"serialnumber=(\w+)"),
        "validfrom": field(r"validfrom=([\d. :]+?),"),
        "validto": field(r"validto=([\d. :]+?)(?:,|$)"),
        "cn": field(r"cn=([^,]+)"),
    }


async def list_certificates():
    certificates = (await call({"plugin": "pfx", "name": "list_all_certificates"})).get(
        "certificates", []
    )
    for certificate in certificates:
        certificate["parsed"] = parse_alias(certificate.get("alias", ""))
    return certificates


def pick_certificate(certificates, serial):
    if not certificates:
        fail("no PFX keys found — put the key into DSKEYS and restart E-IMZO")
    matches = [c for c in certificates
               if serial.lower() == (c["parsed"]["serial"] or "").lower()]
    if not matches:
        available = ", ".join(c["parsed"]["serial"] or "?" for c in certificates)
        fail(f"no key with serial {serial}; available: {available}")
    return matches[0]


async def cmd_keys(_args):
    await apikey()
    out = [{
        "serial": c["parsed"]["serial"],
        "tin": c["parsed"]["tin"],
        "cn": c["parsed"]["cn"],
        "validto": c["parsed"]["validto"],
        "name": c.get("name"),
    } for c in await list_certificates()]
    print(json.dumps(out, ensure_ascii=False, indent=2))


async def cmd_sign(args):
    await apikey()
    certificate = pick_certificate(await list_certificates(), args.serial)
    loaded = await call({
        "plugin": "pfx",
        "name": "load_key",
        "arguments": [
            certificate.get("disk", ""),
            certificate.get("path", ""),
            certificate.get("name", ""),
            certificate.get("alias", ""),
        ],
    })
    key_id = loaded.get("keyId")
    if not key_id:
        fail(f"load_key returned no keyId: {json.dumps(loaded)[:300]}")
    print(json.dumps({"status": "enter the key password in the E-IMZO window "
                      "if it prompts"}, ensure_ascii=False), file=sys.stderr)
    signed = await call({
        "plugin": "pkcs7",
        "name": "create_pkcs7",
        "arguments": [args.data_base64, key_id, "no"],
    })
    print(json.dumps({
        "pkcs7_64": signed.get("pkcs7_64"),
        "signature_hex": signed.get("signature_hex"),
        "signer_serial_number": signed.get("signer_serial_number"),
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(prog="eimzo_sign.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("keys").set_defaults(func=cmd_keys)
    sign = sub.add_parser("sign")
    sign.add_argument("data_base64")
    sign.add_argument("--serial", required=True, help="cert serial from `keys`")
    sign.set_defaults(func=cmd_sign)
    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
