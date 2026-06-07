import os
import hashlib

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import utils as asym_utils
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.exceptions import InvalidSignature

KEYS_DIR = '/app/keys'


def init_keys(keys_dir=KEYS_DIR):
    os.makedirs(keys_dir, exist_ok=True)
    private_path = os.path.join(keys_dir, 'private_key.pem')
    public_path = os.path.join(keys_dir, 'public_key.pem')

    if not os.path.exists(private_path) or not os.path.exists(public_path):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()

        with open(private_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        with open(public_path, 'wb') as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ))

        print(f'[CRYPTO] Llaves generadas en {keys_dir}')


def _load_private_key():
    path = os.path.join(KEYS_DIR, 'private_key.pem')
    with open(path, 'rb') as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _load_public_key():
    path = os.path.join(KEYS_DIR, 'public_key.pem')
    with open(path, 'rb') as f:
        return serialization.load_pem_public_key(f.read())


def sign_data(data: str) -> str:
    private_key = _load_private_key()
    digest = hashlib.sha256(data.encode('utf-8')).digest()
    signature = private_key.sign(
        digest,
        ec.ECDSA(asym_utils.Prehashed(hashes.SHA256())),
    )
    return signature.hex()


def verify_signature(data: str, signature_hex: str) -> bool:
    try:
        public_key = _load_public_key()
        digest = hashlib.sha256(data.encode('utf-8')).digest()
        signature = bytes.fromhex(signature_hex)
        public_key.verify(
            signature,
            digest,
            ec.ECDSA(asym_utils.Prehashed(hashes.SHA256())),
        )
        return True
    except (InvalidSignature, ValueError, Exception):
        return False


def generate_hash(curp: str, id_curso: str, folio: str) -> str:
    data = f'{curp}|{id_curso}|{folio}'
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
