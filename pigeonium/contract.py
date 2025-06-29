from .utils import Utils
from .config import Config
from .state import State
from .struct import Transaction
from .error import *
from asteval import Interpreter


class Contract:
    def __init__(self, script:str) -> None:
        self.script = script
        self.address = Utils.sha3_256(Utils.sha3_256(Utils.sha3_512(script.encode())))[:16]
        self.deployCost = len(script.encode()) * Config.ContractDeployCost
        self.excutionCost = len(script.encode()) * Config.ContractExecutionCost

    def __str__(self):
        return f"<Contract {self.address.hex()}>"
    
    def __repr__(self):
        return self.__str__()
    
    def verify(self):
        return self.address == Utils.sha3_256(Utils.sha3_256(Utils.sha3_512(self.script.encode())))[:16]

    def execute(self, transaction:Transaction, state:State):
        try:
            state.payFee(self.excutionCost)

            contract_config = {
                'augassign': True,
                'if': True,
                'ifexp': True,
                'raise': True
            }

            aeval = Interpreter(minimal=True, config=contract_config)

            aeval.symtable['transaction'] = transaction
            aeval.symtable['selfAddress'] = self.address
            aeval.symtable['baseCurrency'] = Config.BaseCurrency

            aeval.symtable['hex2bytes'] = Utils.hex2bytes
            aeval.symtable['sha256'] = Utils.sha256
            aeval.symtable['sha3_256'] = Utils.sha3_256
            aeval.symtable['sha3_512'] = Utils.sha3_512

            aeval.symtable['CanselTransaction'] = CanselTransaction

            aeval.symtable['getBalance'] = state.getBalance
            aeval.symtable['getCurrency'] = state.getCurrency
            aeval.symtable['getSelfCurrency'] = state.getSelfCurrency
            aeval.symtable['getTransaction'] = state.getTransaction
            aeval.symtable['getTransactions'] = state.getTransactions
            aeval.symtable['getVariable'] = state.getVariable
            # aeval.symtable['getVariables'] = state.getVariables
            aeval.symtable['setVariable'] = state.setVariable
            aeval.symtable['transferFromUser'] = state.transferFromUser
            aeval.symtable['transferFromContract'] = state.transferFromContract
            aeval.symtable['burn'] = state.burn
            aeval.symtable['mint'] = state.mint
            aeval.symtable['createCurrency'] = state.createCurrency
            aeval.symtable['nextIndexId'] = state.nextIndexId

            aeval(self.script)

            if len(aeval.error) > 0:
                errs = {err.exc.__name__: err.msg for err in aeval.error}
                raise ScriptError(errs)
        
        except ScriptError as e: raise
        except PigeoniumError as e: raise
        except Exception as e:
            raise ContractError(str(e))
