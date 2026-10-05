import hashlib
import json
import struct
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa


OID_RSA = "1.2.840.113549.1.1.1"
OID_EC = "1.2.840.10045.2.1"

SIG_ALGS = {
    "1.2.840.113549.1.1.5": (hashes.SHA1, padding.PKCS1v15()),
    "1.2.840.113549.1.1.11": (hashes.SHA256, padding.PKCS1v15()),
    "1.2.840.113549.1.1.12": (hashes.SHA384, padding.PKCS1v15()),
    "1.2.840.113549.1.1.13": (hashes.SHA512, padding.PKCS1v15()),
    "1.2.840.10045.4.1": (hashes.SHA1, None),
    "1.2.840.10045.4.3.2": (hashes.SHA256, None),
    "1.2.840.10045.4.3.3": (hashes.SHA384, None),
    "1.2.840.10045.4.3.4": (hashes.SHA512, None),
}

# APK Signature Scheme v2/v3 signature and content-digest algorithm IDs.
# These are deliberately distinct from the X.509 signatureAlgorithm OIDs.
SIG_ALG_IDS = {
    0x0101: ("rsa-pss", hashes.SHA256),
    0x0102: ("rsa-pss", hashes.SHA512),
    0x0103: ("rsa-pkcs1", hashes.SHA256),
    0x0104: ("rsa-pkcs1", hashes.SHA512),
    0x0201: ("ecdsa", hashes.SHA256),
    0x0202: ("ecdsa", hashes.SHA512),
    0x0301: ("dsa", hashes.SHA256),
}

DIGEST_ALGS = {
    0x0101: hashes.SHA256,
    0x0102: hashes.SHA512,
    0x0103: hashes.SHA256,
    0x0104: hashes.SHA512,
    0x0201: hashes.SHA256,
    0x0202: hashes.SHA512,
    0x0301: hashes.SHA256,
}


def read_tlv(data, off):
    tag = data[off]
    off += 1
    length = data[off]
    off += 1
    if length & 0x80:
        n = length & 0x7F
        length = int.from_bytes(data[off : off + n], "big")
        off += n
    end = off + length
    return tag, data[off:end], end


def read_oid(data, off):
    tag, body, end = read_tlv(data, off)
    if tag != 0x06:
        raise ValueError("expected OID")
    value = body[0] // 40
    rem = body[0] % 40
    parts = [value, rem]
    i = 1
    while i < len(body):
        n = 0
        while True:
            b = body[i]
            i += 1
            n = (n << 7) | (b & 0x7F)
            if not b & 0x80:
                break
        parts.append(n)
    return ".".join(str(p) for p in parts), end


def iter_children(data):
    off = 0
    while off < len(data):
        tag, body, end = read_tlv(data, off)
        yield tag, body
        off = end


def parse_sequence_with_tags(data):
    tag, body, _ = read_tlv(data, 0)
    assert tag == 0x30
    return body


def read_lp(data, off=0):
    length = struct.unpack("<I", data[off : off + 4])[0]
    return data[off + 4 : off + 4 + length], off + 4 + length


def iter_lp(data, off=0):
    while off < len(data):
        body, off = read_lp(data, off)
        yield body


def parse_v2_signer(signer):
    signed_data, off = read_lp(signer, 0)
    signatures, off = read_lp(signer, off)
    public_key, off = read_lp(signer, off)

    sd_off = 0
    digests, sd_off = read_lp(signed_data, sd_off)
    certs, sd_off = read_lp(signed_data, sd_off)
    additional = signed_data[sd_off:]

    digest_records = []
    for entry in iter_lp(digests):
        alg_id = struct.unpack("<I", entry[:4])[0]
        digest, _ = read_lp(entry, 4)
        digest_records.append({"alg_id": alg_id, "digest": digest.hex()})

    certificates = []
    for cert_blob in iter_lp(certs):
        certificates.append(x509.load_der_x509_certificate(cert_blob))

    signature_records = []
    for entry in iter_lp(signatures):
        alg_id = struct.unpack("<I", entry[:4])[0]
        signature, _ = read_lp(entry, 4)
        signature_records.append({"alg_id": alg_id, "signature": signature})

    return signed_data, signature_records, public_key, digest_records, certificates, additional


def verify_v2_signer(signed_data, signature_records, public_key_bytes):
    try:
        public_key = serialization.load_der_public_key(public_key_bytes)
    except Exception:
        try:
            public_key = serialization.load_der_public_key(
                b"\x30" + len(public_key_bytes).to_bytes(1, "big") + public_key_bytes
            )
        except Exception as exc:
            return [{"status": f"public key parse error: {exc}"}]

    results = []
    for record in signature_records:
        alg_id = record["alg_id"]
        sig_bytes = record["signature"]
        alg = SIG_ALG_IDS.get(alg_id)
        if alg is None:
            results.append({"alg_id": alg_id, "status": "unrecognized"})
            continue
        mode, digest_cls = alg
        try:
            if mode == "rsa-pkcs1" and isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    sig_bytes, signed_data, padding.PKCS1v15(), digest_cls()
                )
            elif mode == "rsa-pss" and isinstance(public_key, rsa.RSAPublicKey):
                salt_length = digest_cls.digest_size
                public_key.verify(
                    sig_bytes,
                    signed_data,
                    padding.PSS(
                        mgf=padding.MGF1(digest_cls()),
                        salt_length=salt_length,
                    ),
                    digest_cls(),
                )
            elif mode == "ecdsa" and isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(sig_bytes, signed_data, ec.ECDSA(digest_cls()))
            else:
                raise TypeError(f"{mode} with {type(public_key).__name__}")
            results.append({"alg_id": alg_id, "status": "valid"})
        except InvalidSignature:
            results.append({"alg_id": alg_id, "status": "invalid"})
    return results


def verify_signer(signed_data, signatures_tlv, public_key_bytes, v3):
    public_key = parse_public_key(public_key_bytes)
    sig_entries = parse_signatures(signatures_tlv)
    results = []
    for alg_tlv, sig_bytes in sig_entries:
        oid, _ = read_oid(alg_tlv, 0)
        if oid not in SIG_ALGS:
            results.append({"alg_oid": oid, "status": "unrecognized"})
            continue
        digest_cls, pad = SIG_ALGS[oid]
        try:
            if isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(sig_bytes, signed_data, pad, digest_cls())
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(sig_bytes, signed_data, ec.ECDSA(digest_cls()))
            else:
                raise TypeError(type(public_key).__name__)
            results.append({"alg_oid": oid, "status": "valid"})
        except InvalidSignature:
            results.append({"alg_oid": oid, "status": "invalid"})
    return results


def cert_summary(cert):
    pub = cert.public_key()
    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial": format(cert.serial_number, "x"),
        "not_valid_before": cert.not_valid_before_utc.isoformat(),
        "not_valid_after": cert.not_valid_after_utc.isoformat(),
        "sha256": cert.fingerprint(hashes.SHA256()).hex(),
        "public_key": pub.public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).hex(),
    }


def parse_scheme(value, v3):
    body, _ = read_lp(value, 0)
    signers = []
    for signer in iter_lp(body):
        try:
            if v3:
                # v3 signers insert an 8-byte minSdk/maxSdk pair between
                # signedData and signatures.
                signed_data, off = read_lp(signer, 0)
                min_sdk, max_sdk = struct.unpack("<II", signer[off : off + 8])
                signatures, off = read_lp(signer, off + 8)
                pubkey, off = read_lp(signer, off)
            else:
                min_sdk = max_sdk = None
                signed_data, off = read_lp(signer, 0)
                signatures, off = read_lp(signer, off)
                pubkey, off = read_lp(signer, off)

            sd_off = 0
            digests, sd_off = read_lp(signed_data, sd_off)
            certs, sd_off = read_lp(signed_data, sd_off)
            additional = signed_data[sd_off:]

            digest_records = []
            for entry in iter_lp(digests):
                alg_id = struct.unpack("<I", entry[:4])[0]
                digest, _ = read_lp(entry, 4)
                digest_records.append(
                    {
                        "alg_id": alg_id,
                        "algorithm": DIGEST_ALGS.get(alg_id, hashes.SHA256).name,
                        "digest": digest.hex(),
                    }
                )

            certificates = []
            for cert_blob in iter_lp(certs):
                certificates.append(x509.load_der_x509_certificate(cert_blob))

            signature_records = []
            for entry in iter_lp(signatures):
                alg_id = struct.unpack("<I", entry[:4])[0]
                signature, _ = read_lp(entry, 4)
                signature_records.append(
                    {
                        "alg_id": alg_id,
                        "algorithm": SIG_ALG_IDS.get(alg_id, (None, None))[0],
                        "signature": signature,
                    }
                )
        except Exception as exc:
            signers.append({"error": str(exc)})
            continue
        verification = verify_v2_signer(signed_data, signature_records, pubkey)
        signers.append(
            {
                "verification": verification,
                "certificates": [cert_summary(c) for c in certificates],
                "digests": digest_records,
                "has_additional_attributes": bool(additional),
                "min_sdk": min_sdk,
                "max_sdk": max_sdk,
            }
        )
    return signers


def main(path: Path, out: Path) -> None:
    data = path.read_bytes()
    assert data[-22:-18] == b"PK\x05\x06"
    cd_offset = struct.unpack("<I", data[-6:-2])[0]
    block_size = struct.unpack("<Q", data[cd_offset - 24 : cd_offset - 16])[0]
    block_start = cd_offset - 16 - block_size
    assert data[cd_offset - 16 : cd_offset] == b"APK Sig Block 42"

    pairs = []
    off = block_start + 16
    while off + 8 <= cd_offset - 24:
        size = struct.unpack("<Q", data[off : off + 8])[0]
        block_id = struct.unpack("<I", data[off + 8 : off + 12])[0]
        value = data[off + 12 : off + 8 + size]
        pairs.append((block_id, value))
        off += 8 + size

    result = {"pairs": []}
    for block_id, value in pairs:
        entry = {"id": f"{block_id:08x}", "size": len(value)}
        if block_id == 0x7109871A:
            entry["scheme"] = "APK Signature Scheme v2"
            entry["signers"] = parse_scheme(value, False)
        elif block_id == 0xF05368C0:
            entry["scheme"] = "APK Signature Scheme v3"
            entry["signers"] = parse_scheme(value, True)
        elif block_id == 0x1B93AD61:
            entry["scheme"] = "APK Signature Scheme v3.1"
            entry["signers"] = parse_scheme(value, True)
        else:
            entry["scheme"] = "unrecognized"
            entry["sha256"] = hashlib.sha256(value).hexdigest()
        result["pairs"].append(entry)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"signing pairs={len(pairs)} -> {out}")


if __name__ == "__main__":
    import sys

    main(Path(sys.argv[1]), Path(sys.argv[2]))
