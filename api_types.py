from pydantic import BaseModel, Field
from typing import Union

class Currency(BaseModel):
    currencyId: str
    name: str
    symbol: str
    issuer: str
    supply: int

class NetworkInfo(BaseModel):
    networkName: str
    networkId: int
    contractDeployCost: int
    contractExecutionCost: int
    inputDataCost: int
    decimals: int
    adminPublicKey: str
    baseCurrency: Currency

class Transaction(BaseModel):
    indexId: int
    networkId: int
    source: str
    dest: str
    currencyId: str
    amount: int
    feeAmount: int
    inputData: str
    publicKey: str
    isContract: int
    signature: str
    timestamp: int
    adminSignature: str

class Script(BaseModel):
    script: str

class TransactionPost(BaseModel):
    source: str
    dest: str
    currencyId: str
    amount: int
    feeAmount: int
    inputData: str
    publicKey: str
    signature: str

class ContractPost(BaseModel):
    sender: str
    script: str
    publicKey: str
    signature: str
    deployTransaction: TransactionPost

class ErrorResponse(BaseModel):
    errorCode: str = Field(..., description="エラーの種類を識別するためのコード")
    message: str = Field(..., description="開発者向けのエラーメッセージ")

class ScriptErrorResponse(BaseModel):
    errorCode: str = "ScriptError"
    errors: dict

class InsufficientBalanceErrorResponse(ErrorResponse):
    errorCode: str = "insufficient_balance"
    address: str
    currencyId: str
    amount: int
    balance: int

ErrorResponses = Union[ErrorResponse, InsufficientBalanceErrorResponse]
