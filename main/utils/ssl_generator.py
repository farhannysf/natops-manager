from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
)

from cryptography.x509.oid import NameOID
from datetime import datetime, timezone, timedelta


async def generate_ssl_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "INOP"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "INOP"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "INOP"),
            x509.NameAttribute(NameOID.COMMON_NAME, "INOP"),
        ]
    )

    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("inop")]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    private_key_bytes = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    )

    certificate_bytes = certificate.public_bytes(Encoding.PEM)

    certfile_path = "certfile.crt"
    keyfile_path = "keyfile.key"

    with open(certfile_path, "wb") as cert_file:
        cert_file.write(certificate_bytes)

    with open(keyfile_path, "wb") as key_file:
        key_file.write(private_key_bytes)

    ssl_pair = {
        "certfile": certfile_path,
        "keyfile": keyfile_path,
    }

    return ssl_pair
