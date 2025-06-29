from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import config as Config
from api import router
import pigeonium
from api_types import ErrorResponse, ScriptErrorResponse, InsufficientBalanceErrorResponse

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(pigeonium.PigeoniumError)
async def pigeonium_exception_handler(request: Request, exc: pigeonium.PigeoniumError):
    """
    Pigeoniumライブラリ内で発生したカスタム例外を一元的に処理する
    """
    status_code = status.HTTP_400_BAD_REQUEST
    
    if isinstance(exc, pigeonium.error.InsufficientBalance):
        content = InsufficientBalanceErrorResponse(
            message=str(exc),
            address=exc.address.hex(),
            currencyId=exc.currencyId.hex(),
            amount=exc.amount,
            balance=exc.balance
        )
    elif isinstance(exc, pigeonium.error.ScriptError):
        content = ScriptErrorResponse(message=str(exc), errors=exc.errors)
        print("ScriptError")
        return JSONResponse(status_code=status_code,content={"errorCode": "ScriptError", "errors": exc.errors})
    elif isinstance(exc, pigeonium.error.InvalidSignature):
        content = ErrorResponse(errorCode="InvalidSignature", message=str(exc))
    elif isinstance(exc, pigeonium.error.InvalidTransaction):
        content = ErrorResponse(errorCode="InvalidTransaction", message=str(exc))
    elif isinstance(exc, pigeonium.error.InvalidCurrency):
        content = ErrorResponse(errorCode="InvalidCurrency", message=str(exc))
    elif isinstance(exc, pigeonium.error.DuplicateSignature):
        content = ErrorResponse(errorCode="DuplicateSignature", message=str(exc))
    elif isinstance(exc, pigeonium.error.ContractError):
        content = ErrorResponse(errorCode="ContractError", message=str(exc))
    else:
        content = ErrorResponse(errorCode="PigeoniumError", message=str(exc))
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        status_code=status_code,
        content=content.model_dump(),
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    予期せぬサーバーエラーを処理する
    """
    if isinstance(exc, ValueError):
        status_code=status.HTTP_400_BAD_REQUEST
        content=ErrorResponse(errorCode="ValueError", message=str(exc))
    else:
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        content=ErrorResponse(errorCode="InternalServerError", message=f"An unexpected error occurred: {str(exc)}")

    return JSONResponse(
        status_code=status_code,
        content=content.model_dump()
    )


app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host=Config.Server.Host, port=Config.Server.Port, log_level="debug", root_path=Config.Server.RootPath)
