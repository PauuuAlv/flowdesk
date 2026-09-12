from passlib.context import CryptContext

# bcrypt tiene un límite de 72 bytes en el password; passlib lo trunca solo,
# pero si en el futuro migran a argon2 esto ya no aplica.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
