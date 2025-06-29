from mysql.connector import MySQLConnection as MySqlCon
from .struct import Currency

class Config:
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

    MySQLConnection: MySqlCon = None
