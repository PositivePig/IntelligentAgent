import uvicorn
from app.core.logger import get_logger
import os
from pathlib import Path

logger = get_logger(service="server")

def start_server():
    # 确保工作目录正确
    os.chdir(Path(__file__).parent)
    
    logger.info("Starting server...")
    logger.info(f"Working directory: {os.getcwd()}")
    
    uvicorn.run(
        "main:app",        # 使用模块路径
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        access_log=False,
        log_level=os.getenv("LOG_LEVEL", "error"),
        reload=os.getenv("RELOAD", "true").lower() == "true",
    )

if __name__ == "__main__":
    start_server() 