from .config import Config
from mysql.connector.connection import MySQLConnection
from .error import *
from .currency import Currency
from .struct import Transaction
from .wallet import Wallet
from time import time
from typing import Optional, Literal

class State:
    def __init__(self, userAddress:bytes, contractAddress:bytes, connection:MySQLConnection = Config.MySQLConnection):
        if connection is None:
            connection = Config.MySQLConnection
        connection.ping(reconnect=True,attempts=6,delay=1)
        self.connection = connection
        cursor = connection.cursor(dictionary=True)
        self.cursor = cursor
        self.userAddress = userAddress
        self.contractAddress = contractAddress
    
    def nextIndexId(self):
        self.cursor.execute("SELECT indexId FROM transaction ORDER BY indexId DESC LIMIT 1")
        row = self.cursor.fetchone()
        if row:
            return int(row['indexId']) + 1
        else:
            return 0
    
    def isContract(self, address:bytes):
        self.cursor.execute("SELECT * FROM contract WHERE address=%s", (address,))
        row = self.cursor.fetchone()
        if row is None:
            return False
        return True
    
    def getBalance(self, address:bytes, currencyId:bytes):
        self.cursor.execute("SELECT amount FROM balance WHERE address=%s AND currencyId=%s", (address, currencyId))
        row = self.cursor.fetchone()
        if not row:
            return 0
        return int(row['amount'])
    
    def getBalances(self, address:bytes) -> dict[bytes,int]:
        self.cursor.execute("SELECT * FROM balance WHERE address=%s", (address,))
        balances = {}
        for row in self.cursor.fetchall():
            balances[row['currencyId']] = int(row['amount'])
        return balances

    def getCurrency(self, currencyId:bytes):
        self.cursor.execute("SELECT * FROM currency WHERE currencyId=%s", (currencyId,))
        row = self.cursor.fetchone()
        if not row:
            return None
        cu = Currency()
        cu.currencyId = row['currencyId']
        cu.name = row['name']
        cu.symbol = row['symbol']
        cu.issuer = row['issuer']
        cu.supply = row['supply']
        return cu
    
    def getSelfCurrency(self):
        self.cursor.execute("SELECT * FROM currency WHERE issuer=%s", (self.contractAddress,))
        row = self.cursor.fetchone()
        if not row:
            return None
        cu = Currency()
        cu.currencyId = row['currencyId']
        cu.name = row['name']
        cu.symbol = row['symbol']
        cu.issuer = row['issuer']
        cu.supply = row['supply']
        return cu

    def getScript(self, address:bytes) -> str|None:
        self.cursor.execute("SELECT script FROM contract WHERE address=%s", (address,))
        row = self.cursor.fetchone()
        if not row:
            return None
        return row['script']
    
    def getTransaction(self, indexId:int):
        self.cursor.execute("SELECT * FROM transaction WHERE indexId=%s", (indexId,))
        row = self.cursor.fetchone()
        if not row:
            return None
        return Transaction.fromDict(row)
    
    def getTransactions(
        self,
        address: Optional[bytes] = None,
        source: Optional[bytes] = None,
        dest: Optional[bytes] = None,
        currencyId: Optional[bytes] = None,
        amount_min: Optional[int] = None,
        amount_max: Optional[int] = None,
        timestamp_start: Optional[int] = None,
        timestamp_end: Optional[int] = None,
        isContract: Optional[bool] = None,
        sort_by: Literal["indexId", "timestamp", "amount", "feeAmount"] = "indexId",
        sort_order: Literal["ASC", "DESC"] = "DESC",
        limit: int = 20,
        offset: int = 0
    ) -> list[Transaction]:
        query = "SELECT * FROM transaction"
        conditions = []
        params = []

        if address:
            conditions.append("(source = %s OR dest = %s)")
            params.extend([address, address])
        if source:
            conditions.append("source = %s")
            params.append(source)
        if dest:
            conditions.append("dest = %s")
            params.append(dest)
        if currencyId:
            conditions.append("currencyId = %s")
            params.append(currencyId)
        if amount_min is not None and amount_min >= 0:
            conditions.append("amount >= %s")
            params.append(amount_min)
        if amount_max is not None and amount_max >= 0:
            conditions.append("amount <= %s")
            params.append(amount_max)
        if timestamp_start is not None:
            conditions.append("timestamp >= %s")
            params.append(timestamp_start)
        if timestamp_end is not None:
            conditions.append("timestamp <= %s")
            params.append(timestamp_end)
        if isContract is not None:
            conditions.append("isContract = %s")
            params.append(int(isContract))

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        valid_sort_fields = ["indexId", "timestamp", "amount", "feeAmount"]
        sort_by = sort_by if sort_by in valid_sort_fields else "indexId"
        sort_order = sort_order.upper() if sort_order.upper() in ["ASC", "DESC"] else "DESC"
        query += f" ORDER BY {sort_by} {sort_order} LIMIT %s OFFSET %s"
        limit = limit if (limit > 0 and limit <= 40) else 40
        params.extend([limit, offset])

        self.cursor.execute(query, params)
        transactions = [Transaction.fromDict(row) for row in self.cursor.fetchall()]

        return transactions

    def getVariable(self, address:bytes, varKey:bytes) -> bytes|None:
        self.cursor.execute("SELECT varValue FROM variable WHERE address=%s AND varKey=%s", (address, varKey))
        row = self.cursor.fetchone()
        if not row:
            return None
        return row['varValue']
    
    def getVariables(self, address:bytes) -> dict[bytes,bytes]:
        self.cursor.execute("SELECT * FROM variable WHERE address=%s", (address,))
        variables = {}
        for row in self.cursor.fetchall():
            variables[row['varKey']] = row['varValue']
        return variables
    
    def isDuplicateSignature(self, signature:bytes):
        self.cursor.execute("SELECT indexId FROM transaction WHERE signature=%s", (signature,))
        row = self.cursor.fetchone()
        return False if row is None else True

    def setVariable(self, varKey:bytes, varValue:bytes):
        self.cursor.execute("INSERT INTO variable (address,varKey,varValue) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE varValue=%s",
                            (self.contractAddress, varKey, varValue, varValue))
    
    def transferFromUser(self, dest:bytes, currencyId:bytes, amount:int):
        bal = self.getBalance(self.userAddress, currencyId)
        if bal < amount:
            raise InsufficientBalance(self.userAddress, currencyId, amount, bal)
        if self.userAddress == dest:
            raise SelfTransaction()
        tx = Transaction()
        tx.indexId = self.nextIndexId()
        tx.networkId = Config.NetworkId
        tx.source = self.userAddress
        tx.dest = dest
        tx.currencyId = currencyId
        tx.amount = amount
        tx.feeAmount = 0
        tx.inputData = bytes()
        tx.publicKey = bytes(64)
        tx.isContract = True
        tx.signature = bytes(64)
        tx.timestamp = int(time())
        txData = (tx.indexId.to_bytes(8,'big')+tx.networkId.to_bytes(8,'big')+tx.source+tx.dest+tx.currencyId+tx.amount.to_bytes(8,'big')+tx.feeAmount.to_bytes(8,'big')+tx.inputData+tx.timestamp.to_bytes(8,'big'))
        tx.adminSignature = Wallet.fromPrivate(Config.AdminPrivateKey).sign(txData)
        tx_sql, tx_params = tx.toSql()
        self.cursor.execute(tx_sql, tx_params)
        
        if self.getBalance(self.userAddress, currencyId) == amount:
            self.cursor.execute("DELETE FROM balance WHERE address=%s AND currencyId=%s", (self.userAddress, currencyId))
        else:
            self.cursor.execute("UPDATE balance SET amount=amount-%s WHERE address=%s AND currencyId=%s",
                                (amount, self.userAddress, currencyId))
        if tx.dest == bytes(16):
            self.cursor.execute("UPDATE currency SET supply = supply - %s WHERE currencyId = %s", (amount, currencyId))
        else:
            self.cursor.execute("INSERT INTO balance (address,currencyId,amount) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE amount=amount+%s",
                                (dest, currencyId, amount, amount))
        
        return tx
        
    def transferFromContract(self, dest:bytes, currencyId:bytes, amount:int):
        bal = self.getBalance(self.contractAddress, currencyId)
        if bal < amount:
            raise InsufficientBalance(self.contractAddress, currencyId, amount, bal)
        if self.contractAddress == dest:
            raise SelfTransaction()
        tx = Transaction()
        tx.indexId = self.nextIndexId()
        tx.networkId = Config.NetworkId
        tx.source = self.contractAddress
        tx.dest = dest
        tx.currencyId = currencyId
        tx.amount = amount
        tx.feeAmount = 0
        tx.inputData = bytes()
        tx.publicKey = bytes(64)
        tx.isContract = True
        tx.signature = bytes(64)
        tx.timestamp = int(time())
        txData = (tx.indexId.to_bytes(8,'big')+tx.networkId.to_bytes(8,'big')+tx.source+tx.dest+tx.currencyId+tx.amount.to_bytes(8,'big')+tx.feeAmount.to_bytes(8,'big')+tx.inputData+tx.timestamp.to_bytes(8,'big'))
        tx.adminSignature = Wallet.fromPrivate(Config.AdminPrivateKey).sign(txData)
        tx_sql, tx_params = tx.toSql()
        self.cursor.execute(tx_sql, tx_params)
        
        if self.getBalance(self.contractAddress, currencyId) == amount:
            self.cursor.execute("DELETE FROM balance WHERE address=%s AND currencyId=%s", (self.contractAddress, currencyId))
        else:
            self.cursor.execute("UPDATE balance SET amount=amount-%s WHERE address=%s AND currencyId=%s",
                                (amount, self.contractAddress, currencyId))
        if tx.dest == bytes(16):
            self.cursor.execute("UPDATE currency SET supply = supply - %s WHERE currencyId = %s", (amount, currencyId))
        else:
            self.cursor.execute("INSERT INTO balance (address,currencyId,amount) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE amount=amount+%s",
                                (dest, currencyId, amount, amount))
        
        return tx
    
    def burn(self, amount:int):
        cu = self.getSelfCurrency()
        bal = self.getBalance(self.contractAddress, cu.currencyId)
        if cu and bal >= amount:
            self.cursor.execute("UPDATE currency SET supply=supply-%s WHERE currencyId=%s", (amount, cu.currencyId))
        else:
            raise InsufficientBalance(self.contractAddress, cu.currencyId, amount, bal)
        tx = Transaction()
        tx.indexId = self.nextIndexId()
        tx.networkId = Config.NetworkId
        tx.source = self.contractAddress
        tx.dest = bytes(16)
        tx.currencyId = cu.currencyId
        tx.amount = amount
        tx.feeAmount = 0
        tx.inputData = bytes()
        tx.publicKey = bytes(64)
        tx.isContract = True
        tx.signature = bytes(64)
        tx.timestamp = int(time())
        txData = (tx.indexId.to_bytes(8,'big')+tx.networkId.to_bytes(8,'big')+tx.source+tx.dest+tx.currencyId+tx.amount.to_bytes(8,'big')+tx.feeAmount.to_bytes(8,'big')+tx.inputData+tx.timestamp.to_bytes(8,'big'))
        tx.adminSignature = Wallet.fromPrivate(Config.AdminPrivateKey).sign(txData)
        tx_sql, tx_params = tx.toSql()
        self.cursor.execute(tx_sql, tx_params)
        if self.getBalance(self.contractAddress, cu.currencyId) == amount:
            self.cursor.execute("DELETE FROM balance WHERE address=%s AND currencyId=%s", (self.contractAddress, cu.currencyId))
        else:
            self.cursor.execute("UPDATE balance SET amount=amount-%s WHERE address=%s AND currencyId=%s",
                                (amount, self.contractAddress, cu.currencyId))
        
        self.cursor.execute("UPDATE currency SET amount=amount-%s WHERE currencyId=%s", (amount, cu.currencyId))
        
        return tx
    
    def mint(self, amount:int) -> "Transaction":
        cu = self.getSelfCurrency()
        if not cu: raise InvalidCurrency()
        tx = Transaction()
        tx.indexId = self.nextIndexId()
        tx.networkId = Config.NetworkId
        tx.source = self.contractAddress
        tx.dest = bytes(16)
        tx.currencyId = cu.currencyId
        tx.amount = amount
        tx.feeAmount = 0
        tx.inputData = bytes()
        tx.publicKey = bytes(64)
        tx.isContract = True
        tx.signature = bytes(64)
        tx.timestamp = int(time())
        txData = (tx.indexId.to_bytes(8,'big')+tx.networkId.to_bytes(8,'big')+tx.source+tx.dest+tx.currencyId+tx.amount.to_bytes(8,'big')+tx.feeAmount.to_bytes(8,'big')+tx.inputData+tx.timestamp.to_bytes(8,'big'))
        tx.adminSignature = Wallet.fromPrivate(Config.AdminPrivateKey).sign(txData)
        tx_sql, tx_params = tx.toSql()
        self.cursor.execute(tx_sql, tx_params)
        self.cursor.execute("INSERT INTO balance (address,currencyId,amount) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE amount=amount+%s",
                            (self.contractAddress, cu.currencyId, amount, amount))
        self.cursor.execute("UPDATE currency SET supply=supply+%s WHERE currencyId=%s", (amount, cu.currencyId))
    
        return tx
    
    def deployContract(self, script:str):
        self.cursor.execute("INSERT INTO contract (address,script) VALUES (%s,%s)", (self.contractAddress, script))

    def createCurrency(self, name:str, symbol:str, supply:int) -> "Transaction":
        if self.getSelfCurrency():
            raise InvalidCurrency()
        cu = Currency.create(name,symbol,self.contractAddress,supply)
        tx = Transaction()
        tx.indexId = self.nextIndexId()
        tx.networkId = Config.NetworkId
        tx.source = bytes(16)
        tx.dest = self.contractAddress
        tx.currencyId = cu.currencyId
        tx.amount = supply
        tx.feeAmount = 0
        tx.inputData = bytes()
        tx.publicKey = bytes(64)
        tx.isContract = True
        tx.signature = bytes(64)
        tx.timestamp = int(time())
        txData = (tx.indexId.to_bytes(8,'big')+tx.networkId.to_bytes(8,'big')+tx.source+tx.dest+tx.currencyId+tx.amount.to_bytes(8,'big')+tx.feeAmount.to_bytes(8,'big')+tx.inputData+tx.timestamp.to_bytes(8,'big'))
        tx.adminSignature = Wallet.fromPrivate(Config.AdminPrivateKey).sign(txData)
        tx_sql, tx_params = tx.toSql()
        self.cursor.execute(tx_sql, tx_params)
        self.cursor.execute("INSERT INTO currency (currencyId,name,symbol,issuer,supply) VALUES (%s,%s,%s,%s,%s)",
                            (tx.currencyId, name, symbol, self.contractAddress, supply))
        self.cursor.execute("INSERT INTO balance (address,currencyId,amount) VALUES (%s,%s,%s)",
                            (self.contractAddress, tx.currencyId, tx.amount))
        return tx

    def payFee(self, feeAmount:int):
        bal = self.getBalance(self.userAddress, Config.BaseCurrency.currencyId)
        if bal < feeAmount:
            raise InsufficientBalance(self.userAddress, Config.BaseCurrency.currencyId, feeAmount, bal)
        self.transferFromUser(bytes(16), Config.BaseCurrency.currencyId, feeAmount)
