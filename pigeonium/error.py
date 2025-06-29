class PigeoniumError(Exception):
    pass

class ContractError(PigeoniumError):
    def __init__(self, message="Contract error"):
        super().__init__(message)

class CanselTransaction(PigeoniumError):
    def __init__(self, reason:str):
        reason_str = str(reason)
        self.reason = reason_str
        super().__init__(reason_str)

class ScriptError(ContractError):
    def __init__(self, errors:dict):
        self.errors = errors
        super().__init__(errors)

class InvalidSignature(ContractError):
    def __init__(self, message="Invalid signature"):
        super().__init__(message)

class InsufficientBalance(ContractError):
    def __init__(self, address:bytes, currencyId:bytes, amount:int, balance:int):
        self.address = address
        self.currencyId = currencyId
        self.amount = amount
        self.balance = balance
        super().__init__(f"Insufficient balance")

class InvalidTransaction(ContractError):
    def __init__(self, message="Invalid transaction"):
        super().__init__(message)

class InvalidCurrency(ContractError):
    def __init__(self, message="Invalid currency"):
        super().__init__(message)

class SelfTransaction(ContractError):
    def __init__(self, message="Self transaction"):
        super().__init__(message)

class DuplicateSignature(ContractError):
    def __init__(self, message="Duplicate signature"):
        super().__init__(message)

class InvalidAdminSignature(PigeoniumError):
    def __init__(self, message="Invalid admin signature"):
        super().__init__(message)
