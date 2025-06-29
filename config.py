from pigeonium.currency import Currency

class Server:
    Host: str = "0.0.0.0"
    Port: int = 14540
    RootPath: str = "/"

class MySQL:
    host: str = "localhost"
    user: str = "pigeonium"
    password: str = "password"
    database: str = "pigeonium"

class Pigeonium:
    NetworkName: str = "Pigeonium"
    NetworkId: int = 0
    ContractDeployCost: int = 100
    ContractExecutionCost: int = 10
    InputDataCost: int = 10
    Decimals: int = 6

    AdminPrivateKey: bytes = bytes(32)
    AdminPublicKey: bytes = bytes(64)

    BaseCurrency = Currency()
    BaseCurrency.currencyId = bytes(16)
    BaseCurrency.name = "Pigeon"
    BaseCurrency.symbol = "Pigeon"
    BaseCurrency.issuer = bytes(16)
    BaseCurrency.supply = 1000000_000000 # = 1000000.000000
