from fastapi import APIRouter, HTTPException
import mysql.connector
import pigeonium
from pydantic import BaseModel
import api_types
from typing import Literal, Optional
import config as ServerConfig
from time import time

router = APIRouter()

pigeonium.Config.NetworkName = ServerConfig.Pigeonium.NetworkName
pigeonium.Config.NetworkId = ServerConfig.Pigeonium.NetworkId
pigeonium.Config.ContractDeployCost = ServerConfig.Pigeonium.ContractDeployCost
pigeonium.Config.ContractExecutionCost = ServerConfig.Pigeonium.ContractExecutionCost
pigeonium.Config.InputDataCost = ServerConfig.Pigeonium.InputDataCost
pigeonium.Config.Decimals = ServerConfig.Pigeonium.Decimals
pigeonium.Config.AdminPrivateKey = ServerConfig.Pigeonium.AdminPrivateKey
pigeonium.Config.AdminPublicKey = ServerConfig.Pigeonium.AdminPublicKey

pigeonium.Config.BaseCurrency = ServerConfig.Pigeonium.BaseCurrency

pigeonium.Config.MySQLConnection = mysql.connector.connect(
    host=ServerConfig.MySQL.host, user=ServerConfig.MySQL.user,
    password=ServerConfig.MySQL.password, database=ServerConfig.MySQL.database
)

def create_genesis_tx():
    state = pigeonium.State(bytes(16), bytes(16))
    if state.getTransaction(0) is None and state.getCurrency(pigeonium.Config.BaseCurrency.currencyId) is None:
        state.cursor.execute(
            "INSERT INTO currency (currencyId,name,symbol,issuer,supply) VALUES (%s,%s,%s,%s,%s)", 
            (
                pigeonium.Config.BaseCurrency.currencyId, pigeonium.Config.BaseCurrency.name, pigeonium.Config.BaseCurrency.symbol,
                pigeonium.Config.BaseCurrency.issuer, pigeonium.Config.BaseCurrency.supply
            )
        )
        admin_wallet = pigeonium.Wallet.fromPrivate(pigeonium.Config.AdminPrivateKey)
        genesis_tx = pigeonium.Transaction.genesis(
            adminWallet=admin_wallet,
            dest=pigeonium.Config.BaseCurrency.issuer,
            currencyId=pigeonium.Config.BaseCurrency.currencyId,
            amount=pigeonium.Config.BaseCurrency.supply,
            timestamp=int(time())
        )
        genesis_tx.execute()
        state.cursor.close()
        pigeonium.Config.MySQLConnection.commit()

create_genesis_tx()

@router.get("/")
async def root() -> api_types.NetworkInfo:
    response = api_types.NetworkInfo(
        networkName=pigeonium.Config.NetworkName,
        networkId=pigeonium.Config.NetworkId,
        contractDeployCost=pigeonium.Config.ContractDeployCost,
        contractExecutionCost=pigeonium.Config.ContractExecutionCost,
        inputDataCost=pigeonium.Config.InputDataCost,
        decimals=pigeonium.Config.Decimals,
        adminPublicKey=pigeonium.Config.AdminPublicKey.hex(),
        baseCurrency=api_types.Currency(
            currencyId=pigeonium.Config.BaseCurrency.currencyId.hex(),
            name=pigeonium.Config.BaseCurrency.name,
            symbol=pigeonium.Config.BaseCurrency.symbol,
            issuer=pigeonium.Config.BaseCurrency.issuer.hex(),
            supply=pigeonium.Config.BaseCurrency.supply
        )
    )
    return response

@router.get("/currency/{currencyId}")
async def get_currency(currencyId:str) -> api_types.Currency:
    argCurrencyId = bytes.fromhex(currencyId)
    cu = pigeonium.State(bytes(16), bytes(16)).getCurrency(argCurrencyId)
    if cu is None:
        raise HTTPException(status_code=400, detail="Invalid currency")
    return api_types.Currency(
        currencyId=cu.currencyId.hex(),
        name=cu.name, symbol=cu.symbol,
        issuer=cu.issuer.hex(), supply=cu.supply
    )

@router.get("/balance/{address}/{currencyId}")
async def get_balance(address:str, currencyId:str):
    argAddress = bytes.fromhex(address)
    return {"currencyId": currencyId, "amount": pigeonium.State(argAddress, bytes(16)).getBalance(argAddress, bytes.fromhex(currencyId))}

@router.get("/balances/{address}")
async def get_balances(address:str):
    argAddress = bytes.fromhex(address)
    balances = pigeonium.State(argAddress, bytes(16)).getBalances(argAddress)
    response = {}
    for currencyId, amount in balances.items():
        response[currencyId.hex()] = amount
    return response

@router.get("/transaction/{indexId}")
async def get_transaction(indexId:int) -> api_types.Transaction:
    try:
        transaction = pigeonium.State(bytes(16), bytes(16)).getTransaction(indexId)
        if transaction is None:
            return {}
        else:
            transaction.networkId = pigeonium.Config.NetworkId
            return api_types.Transaction(**transaction.toHexDict())
    except Exception as e:
        if pigeonium.Config.MySQLConnection.is_connected():
            pigeonium.Config.MySQLConnection.rollback()
        raise e

@router.get("/transactions")
async def get_transactions(
    address: Optional[str] = None,
    source: Optional[str] = None,
    dest: Optional[str] = None,
    currencyId: Optional[str] = None,
    amount_min: Optional[int] = None,
    amount_max: Optional[int] = None,
    timestamp_start: Optional[int] = None,
    timestamp_end: Optional[int] = None,
    isContract: Optional[bool] = None,
    sort_by: Literal["indexId", "timestamp", "amount", "feeAmount"] = "indexId",
    sort_order: Literal["ASC", "DESC"] = "DESC",
    limit: int = 20,
    offset: int = 0
) -> list[api_types.Transaction]:
    try:
        state = pigeonium.State(bytes(16), bytes(16))
        transactions = state.getTransactions(
            address=bytes.fromhex(address) if address else None,
            source=bytes.fromhex(source) if source else None,
            dest=bytes.fromhex(dest) if dest else None,
            currencyId=bytes.fromhex(currencyId) if currencyId else None,
            amount_min=amount_min,
            amount_max=amount_max,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            isContract=isContract,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit if limit > 0 and limit <= 40 else 20,
            offset=offset
        )
        response = []
        for transaction in transactions:
            transaction.networkId = pigeonium.Config.NetworkId
            response.append(api_types.Transaction(**transaction.toHexDict()))
        return response
    
    except Exception as e:
        if pigeonium.Config.MySQLConnection.is_connected():
            pigeonium.Config.MySQLConnection.rollback()
        raise e
    finally:
        if state and state.cursor:
            state.cursor.close()

@router.get("/variable/{address}/{varKey}")
async def get_variable(address:str, varKey:str):
    argAddress = bytes.fromhex(address)
    argVarKey = bytes.fromhex(varKey)
    varValue = pigeonium.State(argAddress, bytes(16)).getVariable(argAddress, argVarKey)
    return {"varKey": varKey, "varValue": varValue.hex() if varValue is not None else None}

@router.get("/script/{address}")
async def get_script(address:str) -> api_types.Script:
    argAddress = bytes.fromhex(address)
    script = pigeonium.State(argAddress, bytes(16)).getScript(argAddress)
    return api_types.Script(script=script)

@router.get("/is_contract/{address}")
async def is_contract(address:str):
    try:
        argAddress = bytes.fromhex(address)
        state = pigeonium.State(argAddress, bytes(16))
        is_contract = state.isContract(argAddress)
        state.cursor.close()
        return {"isContract": is_contract}
    except Exception as e:
        if pigeonium.Config.MySQLConnection.is_connected():
            pigeonium.Config.MySQLConnection.rollback()
        raise e

@router.post("/transaction")
async def post_transaction(transaction:api_types.TransactionPost) -> api_types.Transaction:
    try:
        tx = pigeonium.Transaction()
        tx.networkId = pigeonium.Config.NetworkId
        tx.source = bytes.fromhex(transaction.source)
        tx.dest = bytes.fromhex(transaction.dest)
        tx.currencyId = bytes.fromhex(transaction.currencyId)
        tx.amount = transaction.amount
        tx.feeAmount = transaction.feeAmount
        tx.inputData = bytes.fromhex(transaction.inputData)
        tx.publicKey = bytes.fromhex(transaction.publicKey)
        tx.signature = bytes.fromhex(transaction.signature)
        tx.isContract = False
        tx_v = tx.verify()
        if not tx_v[0]:
            raise HTTPException(status_code=400, detail="Invalid transaction")
        state = pigeonium.State(bytes(16), bytes(16))
        if state.isDuplicateSignature(tx.signature):
            raise pigeonium.error.InvalidSignature()
        tx.adminSign(state.nextIndexId(), pigeonium.Wallet.fromPrivate(pigeonium.Config.AdminPrivateKey))
        state.cursor.close()
        tx.execute()
        pigeonium.Config.MySQLConnection.commit()
        return api_types.Transaction(**tx.toHexDict())
    except Exception as e:
        if pigeonium.Config.MySQLConnection.is_connected():
            pigeonium.Config.MySQLConnection.rollback()
        raise e
    finally:
        if state and state.cursor:
            state.cursor.close()

@router.post("/contract")
async def post_contract(contractPost:api_types.ContractPost) -> api_types.Transaction:
    try:
        senderBin = bytes.fromhex(contractPost.sender)
        publicKeyBin = bytes.fromhex(contractPost.publicKey)
        signatureBin = bytes.fromhex(contractPost.signature)
        contract = pigeonium.Contract(contractPost.script)
        senderWallet = pigeonium.Wallet.fromPublic(publicKeyBin)
        tx = pigeonium.Transaction()
        tx.networkId = pigeonium.Config.NetworkId
        tx.source = senderWallet.address
        tx.dest = bytes(16)
        tx.currencyId = pigeonium.Config.BaseCurrency.currencyId
        tx.amount = contract.deployCost
        tx.feeAmount = 0
        tx.inputData = contract.address
        tx.publicKey = publicKeyBin
        tx.signature = bytes.fromhex(contractPost.deployTransaction.signature)
        tx.isContract = False
        tx_v = tx.verify()
        if not tx_v[0]:
            raise HTTPException(status_code=400, detail="Invalid transaction")
        if not (senderBin == tx.source) or not (senderWallet.address == tx.source) or senderWallet.verifySignature(pigeonium.Utils.sha256(contract.script.encode()), signatureBin) is False:
            raise HTTPException(status_code=400, detail="Invalid sender")
        state = pigeonium.State(bytes(16), contract.address)
        if state.getScript(contract.address) is not None:
            raise HTTPException(status_code=400, detail="Contract already deployed")
        tx.adminSign(state.nextIndexId(), pigeonium.Wallet.fromPrivate(pigeonium.Config.AdminPrivateKey))

        tx.execute()

        state.deployContract(contract.script)
        state.cursor.close()
        pigeonium.Config.MySQLConnection.commit()
        return api_types.Transaction(**tx.toHexDict())
    except Exception as e:
        if pigeonium.Config.MySQLConnection.is_connected():
            pigeonium.Config.MySQLConnection.rollback()
        raise e
    finally:
        if state and state.cursor:
            state.cursor.close()
